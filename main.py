import os
import sys
import json
import fitz

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget, QLabel, QComboBox, QHBoxLayout, QFrame, 
                               QFileDialog, QLineEdit, QListWidget, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QMenu, QAbstractItemView, 
                               QStackedWidget, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QIcon, QPixmap

__app_name__ = "QpdfTool"
__version__ = "1.0.2"
__author__ = "QwejayHuang"
__description__ = "极简风格的PDF处理工具"

GLOBAL_QSS = """
    QMainWindow {
        background-color: #0f172a;
    }
    
    QLabel {
        color: #94a3b8;
        font-size: 13px;
        font-weight: 500;
    }

    QListWidget#SidebarNav {
        background-color: #090d16;
        border: none;
        outline: none;
    }
    QListWidget#SidebarNav::item {
        padding: 12px 16px;
        margin: 4px 12px;
        color: #94a3b8;
        font-size: 13px;
        font-weight: 600;
        border-radius: 8px;
        border: none;
    }
    QListWidget#SidebarNav::item:hover {
        background-color: #1e293b;
        color: #f1f5f9;
    }
    QListWidget#SidebarNav::item:selected {
        background-color: #3b82f6;
        color: #ffffff;
    }

    QTableWidget {
        border: 1px solid #1e293b;
        border-radius: 10px;
        background-color: #0b0f19;
        font-size: 13px;
        outline: none;
        gridline-color: transparent;
    }
    QTableWidget::item {
        padding: 10px 12px;
        border-bottom: 1px solid #1e293b;
        color: #e2e8f0;
    }
    QTableWidget::item:selected {
        background-color: #1e293b;
        color: #3b82f6;
    }
    QHeaderView::section {
        background-color: #0f172a;
        color: #64748b;
        padding: 10px;
        border: none;
        border-bottom: 1px solid #1e293b;
        font-weight: bold;
    }

    QComboBox, QLineEdit {
        border: 1px solid #1e293b;
        border-radius: 8px;
        font-size: 13px;
        color: #f8fafc;
        background-color: #131b2e;
        padding: 6px 12px;
    }
    QComboBox:hover, QLineEdit:focus {
        border-color: #3b82f6;
    }
    QComboBox::drop-down {
        border: none;
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 30px;
    }
    QComboBox QAbstractItemView {
        background-color: #131b2e;
        border: 1px solid #1e293b;
        selection-background-color: #3b82f6;
        selection-color: #ffffff;
        color: #e2e8f0;
        outline: none;
        border-radius: 8px;
        padding: 4px;
    }

    QPushButton {
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        padding: 8px 16px;
    }
    QPushButton.action {
        background-color: #3b82f6;
        color: #ffffff;
        border: none;
    }
    QPushButton.action:hover {
        background-color: #2563eb;
    }
    QPushButton.action:pressed {
        background-color: #1d4ed8;
    }
    QPushButton.stop {
        background-color: #ef4444;
        color: #ffffff;
        border: none;
    }
    QPushButton.stop:hover {
        background-color: #dc2626;
    }
    QPushButton.stop:pressed {
        background-color: #b91c1c;
    }

    QScrollBar:vertical {
        border: none;
        background: #0f172a;
        width: 8px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #1e293b;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical:hover {
        background: #334155;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
"""


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self, allowed_exts, prompt_text, parent=None):
        super().__init__(parent)
        self.allowed_exts = allowed_exts
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: #131b2e;
                border: 2px dashed #1e293b;
                border-radius: 12px;
            }
            QFrame:hover {
                background-color: #1c2741;
                border-color: #3b82f6;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self.icon_label = QLabel("📤")
        self.icon_label.setStyleSheet("font-size: 24px; background: transparent; border: none;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        self.label = QLabel(prompt_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    background-color: #1c2741;
                    border: 2px dashed #3b82f6;
                    border-radius: 12px;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                background-color: #131b2e;
                border: 2px dashed #1e293b;
                border-radius: 12px;
            }
            QFrame:hover {
                background-color: #1c2741;
                border-color: #3b82f6;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        self.dragLeaveEvent(event)
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and os.path.splitext(path)[1].lower() in self.allowed_exts:
                files.append(path)
            elif os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for fname in filenames:
                        fp = os.path.join(root, fname)
                        if os.path.splitext(fp)[1].lower() in self.allowed_exts: 
                            files.append(fp)
        if files: 
            self.files_dropped.emit(files)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter(f"支持的文件 ({' '.join([f'*{ext}' for ext in self.allowed_exts])})")
            if dialog.exec():
                files = [p for p in dialog.selectedFiles() if os.path.splitext(p)[1].lower() in self.allowed_exts]
                if files: 
                    self.files_dropped.emit(files)


class FileTableWidget(QTableWidget):
    def __init__(self, is_sortable=False, parent=None):
        super().__init__(parent)
        self.is_sortable = is_sortable
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["文件名", "格式", "状态"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 120)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #131b2e;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
                color: #e2e8f0;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #1e293b;
                margin: 6px 4px;
            }
        """)
        row = self.rowAt(pos.y())
        if row >= 0:
            if self.is_sortable:
                menu.addAction("↑ 上移", lambda: self.move_row(row, -1))
                menu.addAction("↓ 下移", lambda: self.move_row(row, 1))
                menu.addSeparator()
            menu.addAction("❌ 移除", lambda: self.removeRow(row))
            menu.addSeparator()
        menu.addAction("🗑️ 清空列表", lambda: self.setRowCount(0))
        menu.exec(self.mapToGlobal(pos))

    def move_row(self, row, offset):
        target = row + offset
        if target < 0 or target >= self.rowCount(): 
            return
        self.setUpdatesEnabled(False)
        self.insertRow(target + (1 if offset > 0 else 0))
        src = row + (1 if offset > 0 else 0)
        for col in range(self.columnCount()):
            self.setItem(target + (0 if offset > 0 else 1), col, self.takeItem(src, col))
        self.removeRow(src)
        self.selectRow(target + (0 if offset > 0 else 1))
        self.setUpdatesEnabled(True)

    def add_files(self, files):
        existing = {self.item(i, 0).data(Qt.UserRole) for i in range(self.rowCount())}
        for f in files:
            if f in existing: 
                continue
            r = self.rowCount()
            self.insertRow(r)
            
            name_item = QTableWidgetItem(os.path.basename(f))
            name_item.setData(Qt.UserRole, f)
            self.setItem(r, 0, name_item)
            
            ext = os.path.splitext(f)[1][1:].upper()
            ext_item = QTableWidgetItem(ext)
            ext_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(r, 1, ext_item)
            
            status_item = QTableWidgetItem("待处理")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QColor("#64748b"))
            self.setItem(r, 2, status_item)
            existing.add(f)
        self.scrollToBottom()

    def get_files(self):
        return [self.item(i, 0).data(Qt.UserRole) for i in range(self.rowCount())]

    def update_status(self, file_path, status, is_error=False):
        for i in range(self.rowCount()):
            if self.item(i, 0).data(Qt.UserRole) == file_path:
                status_item = self.item(i, 2)
                status_item.setText(status)
                status_item.setForeground(QColor("#ef4444" if is_error else "#10b981"))
                self.scrollToItem(self.item(i, 0))
                break


class TaskWorkspace(QWidget):
    def __init__(self, task_id, title, allowed_exts, is_sortable=False):
        super().__init__()
        self.task_id = task_id
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel(title)
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        layout.addWidget(header)

        self.drop_area = DropArea(allowed_exts, f"点击或拖拽 {','.join(allowed_exts).upper()} 文件到此处")
        self.drop_area.setFixedHeight(100)
        layout.addWidget(self.drop_area)

        self.table = FileTableWidget(is_sortable=is_sortable)
        self.drop_area.files_dropped.connect(self.table.add_files)
        layout.addWidget(self.table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #131b2e;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.control_layout = QHBoxLayout()
        self.control_layout.setSpacing(12)
        layout.addLayout(self.control_layout)

    def add_control(self, widget):
        self.control_layout.addWidget(widget)

    def add_stretch(self):
        self.control_layout.addStretch()
        
    def setup_dynamic_input(self, combo: QComboBox, line_edit: QLineEdit, rules: dict):
        def update_ui(text):
            for key, prompt in rules.items():
                if key in text:
                    if prompt is None:
                        line_edit.clear()
                        line_edit.setPlaceholderText("此模式无需填写参数")
                        line_edit.setEnabled(False)
                        line_edit.setStyleSheet("""
                            QLineEdit {
                                background-color: #0b0f19;
                                border: 1px solid #1e293b;
                                color: #475569;
                            }
                        """)
                    else:
                        line_edit.setPlaceholderText(prompt)
                        line_edit.setEnabled(True)
                        line_edit.setStyleSheet("""
                            QLineEdit {
                                background-color: #131b2e;
                                border: 1px solid #1e293b;
                                color: #f8fafc;
                            }
                            QLineEdit:focus {
                                border-color: #3b82f6;
                            }
                        """)
                    break
        combo.currentTextChanged.connect(update_ui)
        update_ui(combo.currentText())


class ConvertWorker(QThread):
    progress = Signal(str, str, bool)
    finished = Signal(int)

    def __init__(self, task_id, files, settings):
        super().__init__()
        self.task_id = task_id
        self.files = files
        self.settings = settings
        self._is_running = True

    def run(self):
        success_count = 0
        for f in self.files:
            if not self._is_running: 
                break
            try:
                if self.task_id == "pdf_word":
                    ext = os.path.splitext(f)[1].lower()
                    if ext == '.pdf':
                        try:
                            from pdf2docx import Converter
                        except ImportError:
                            raise ImportError("需安装 pdf2docx 库")
                        out = os.path.join(self._get_out_dir(f), f"{os.path.splitext(os.path.basename(f))[0]}.docx")
                        cv = Converter(f)
                        cv.convert(out, start=0, end=None)
                        cv.close()
                        self.progress.emit(f, "转为 Word 成功", False)
                    elif ext == '.docx':
                        try:
                            from docx2pdf import convert as docx2pdf_convert
                        except ImportError:
                            raise ImportError("需安装 docx2pdf 库 (且依赖本地Office)")
                        out = os.path.join(self._get_out_dir(f), f"{os.path.splitext(os.path.basename(f))[0]}.pdf")
                        docx2pdf_convert(f, out)
                        self.progress.emit(f, "转为 PDF 成功", False)

                elif self.task_id == "pdf2img":
                    count = self._pdf_to_images(f)
                    self.progress.emit(f, f"成功 ({count}页)", False)
                elif self.task_id == "pdf_split":
                    self._split_pdf(f, self.settings.get("split_mode"), self.settings.get("page_range"))
                    self.progress.emit(f, "操作成功", False)
                elif self.task_id == "pdf_compress":
                    saved_kb = self._compress_pdf(f)
                    self.progress.emit(f, f"减小 {saved_kb:.1f}KB", False)
                elif self.task_id == "pdf_extract":
                    self._extract_content(f, self.settings.get("ext_mode"))
                    self.progress.emit(f, "提取成功", False)
                elif self.task_id == "pdf_security":
                    self._security_pdf(f, self.settings.get("sec_mode"), self.settings.get("sec_param"))
                    self.progress.emit(f, "处理成功", False)
                elif self.task_id == "pdf_edit":
                    self._edit_pages(f, self.settings.get("edit_mode"), self.settings.get("edit_param"))
                    self.progress.emit(f, "重组成功", False)
                elif self.task_id == "pdf_attach":
                    self._attach_file(f, self.settings.get("attach_mode"), self.settings.get("attach_param"))
                    self.progress.emit(f, "附加成功", False)
                success_count += 1
            except Exception as e:
                self.progress.emit(f, f"失败 ({str(e)})", True)

        if self._is_running and self.files:
            if self.task_id == "img2pdf":
                if self.settings.get("img_pdf_mode") == "合并":
                    try:
                        self._merge_images_to_pdf(self.files)
                        for img in self.files: 
                            self.progress.emit(img, "已合并", False)
                        success_count = 1
                    except Exception:
                        for img in self.files: 
                            self.progress.emit(img, "失败", True)
                else:
                    for f in self.files:
                        if not self._is_running: 
                            break
                        try:
                            self._single_image_to_pdf(f)
                            self.progress.emit(f, "成功", False)
                            success_count += 1
                        except Exception: 
                            self.progress.emit(f, "失败", True)
            elif self.task_id == "pdf_merge":
                try:
                    self._merge_pdfs(self.files)
                    for f in self.files: 
                        self.progress.emit(f, "已合并", False)
                    success_count = 1
                except Exception:
                    for f in self.files: 
                        self.progress.emit(f, "失败", True)

        self.finished.emit(success_count)

    def _get_out_dir(self, file_path):
        d = self.settings.get("out_dir", "").strip()
        return d if d and os.path.isdir(d) else os.path.dirname(file_path)

    def _pdf_to_images(self, pdf_path):
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        out_folder = os.path.join(self._get_out_dir(pdf_path), f"{base}_图片")
        os.makedirs(out_folder, exist_ok=True)
        dpi = int(self.settings.get("pdf_dpi", 150))
        fmt = self.settings.get("pdf_img_fmt", "png").lower()
        doc = fitz.open(pdf_path)
        for page in doc:
            if not self._is_running: 
                break
            page.get_pixmap(dpi=dpi).save(os.path.join(out_folder, f"第{page.number + 1}页.{fmt}"))
        count = len(doc)
        doc.close()
        return count

    def _single_image_to_pdf(self, img_path):
        out = os.path.join(self._get_out_dir(img_path), f"{os.path.splitext(os.path.basename(img_path))[0]}.pdf")
        doc = fitz.open("pdf", fitz.open(img_path).convert_to_pdf())
        doc.save(out)
        doc.close()

    def _merge_images_to_pdf(self, imgs):
        out = os.path.join(self._get_out_dir(imgs[0]), "图片合并文档.pdf")
        doc = fitz.open()
        for img in imgs:
            if not self._is_running: 
                break
            img_doc = fitz.open("pdf", fitz.open(img).convert_to_pdf())
            doc.insert_pdf(img_doc)
            img_doc.close()
        doc.save(out)
        doc.close()

    def _merge_pdfs(self, pdfs):
        out = os.path.join(self._get_out_dir(pdfs[0]), "合并的PDF文档.pdf")
        doc = fitz.open()
        for pdf in pdfs:
            if not self._is_running: 
                break
            src = fitz.open(pdf)
            doc.insert_pdf(src)
            src.close()
        doc.save(out)
        doc.close()

    def _split_pdf(self, pdf_path, mode, range_str):
        doc = fitz.open(pdf_path)
        target_pages = set()
        if not range_str.strip(): 
            raise ValueError("未输入页码范围")
        for part in range_str.split(','):
            part = part.strip()
            if not part: 
                continue
            if '-' in part:
                start, end = map(int, part.split('-'))
                target_pages.update(range(start - 1, end))
            else:
                target_pages.add(int(part) - 1)
                
        all_pages = set(range(len(doc)))
        if "删除" in mode: 
            final_pages = sorted(list(all_pages - target_pages))
        else: 
            final_pages = sorted([p for p in target_pages if p in all_pages])
        
        if not final_pages: 
            raise ValueError("操作后文档为空")
        doc.select(final_pages)
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        doc.save(os.path.join(self._get_out_dir(pdf_path), f"{base}_已处理.pdf"))
        doc.close()

    def _compress_pdf(self, pdf_path):
        orig = os.path.getsize(pdf_path)
        out = os.path.join(self._get_out_dir(pdf_path), f"{os.path.splitext(os.path.basename(pdf_path))[0]}_压缩.pdf")
        doc = fitz.open(pdf_path)
        doc.save(out, garbage=4, deflate=True)
        doc.close()
        return (orig - os.path.getsize(out)) / 1024.0

    def _extract_content(self, pdf_path, mode):
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        out_dir = os.path.join(self._get_out_dir(pdf_path), f"{base}_提取内容")
        os.makedirs(out_dir, exist_ok=True)
        doc = fitz.open(pdf_path)
        
        if "纯文本" in mode:
            with open(os.path.join(out_dir, f"{base}_文本.txt"), "w", encoding="utf-8") as f:
                for page in doc: 
                    f.write(page.get_text() + "\n\n")
        elif "图片" in mode:
            for p_num, page in enumerate(doc):
                for i_num, img in enumerate(page.get_images()):
                    pix = fitz.Pixmap(doc, img[0])
                    if pix.n - pix.alpha > 3: 
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    pix.save(os.path.join(out_dir, f"页{p_num+1}_图{i_num+1}.png"))
        elif "表格" in mode:
            with open(os.path.join(out_dir, f"{base}_表格.json"), "w", encoding="utf-8") as f:
                all_tabs = []
                for p_num, page in enumerate(doc):
                    for tab in page.find_tables().tables:
                        all_tabs.append({"page": p_num+1, "data": tab.extract()})
                json.dump(all_tabs, f, ensure_ascii=False, indent=2)
        elif "矢量图形" in mode:
            with open(os.path.join(out_dir, f"{base}_矢量绘图.json"), "w", encoding="utf-8") as f:
                all_draws = []
                for p_num, page in enumerate(doc):
                    drawings = page.get_drawings()
                    if drawings: 
                        all_draws.append({"page": p_num+1, "paths_count": len(drawings)})
                json.dump(all_draws, f, ensure_ascii=False, indent=2)
        doc.close()

    def _security_pdf(self, pdf_path, mode, param):
        if not param.strip() and "解密" not in mode: 
            raise ValueError("参数为空")
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        doc = fitz.open(pdf_path)
        if "加密" in mode:
            doc.save(os.path.join(self._get_out_dir(pdf_path), f"{base}_加密.pdf"), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=param, owner_pw=param)
        elif "解密" in mode:
            if not doc.authenticate(param): 
                raise ValueError("密码错误")
            doc.save(os.path.join(self._get_out_dir(pdf_path), f"{base}_解密.pdf"))
        elif "打黑" in mode:
            for page in doc:
                for inst in page.search_for(param): 
                    page.add_redact_annot(inst, fill=(0,0,0))
                page.apply_redactions()
            doc.save(os.path.join(self._get_out_dir(pdf_path), f"{base}_打码.pdf"))
        doc.close()

    def _edit_pages(self, pdf_path, mode, param):
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        doc = fitz.open(pdf_path)
        out = os.path.join(self._get_out_dir(pdf_path), f"{base}_页面操作.pdf")
        
        if "旋转" in mode:
            deg = 90 if "顺时针" in mode else -90
            for page in doc: 
                page.set_rotation(page.rotation + deg)
            doc.save(out)
        elif "裁剪" in mode:
            try: 
                x0, y0, x1, y1 = map(float, [x.strip() for x in param.split(',')])
            except Exception: 
                raise ValueError("坐标格式错误")
            for page in doc: 
                page.set_cropbox(fitz.Rect(x0, y0, x1, y1))
            doc.save(out)
        elif "添加水印" in mode:
            if not os.path.exists(param): 
                raise ValueError("图片不存在")
            for page in doc: 
                page.insert_image(page.bound(), filename=param, overlay=True)
            doc.save(out)
        elif "插入空白页" in mode:
            doc.new_page(-1)
            doc.save(out)
        elif "插入文本页" in mode:
            if not param: 
                raise ValueError("文本为空")
            doc.insert_page(-1, text=param, fontsize=12)
            doc.save(out)
        elif "单页拆为四页" in mode:
            doc2 = fitz.open()
            for spage in doc:
                r1 = spage.rect / 2
                rects = [r1, r1 + (r1.width, 0, r1.width, 0), r1 + (0, r1.height, 0, r1.height), fitz.Rect(r1.br, spage.rect.br)]
                for rx in rects:
                    page = doc2.new_page(-1, width=rx.width, height=rx.height)
                    page.show_pdf_page(page.rect, doc, spage.number, clip=rx)
            doc2.save(out)
            doc2.close()
        elif "四合一拼版" in mode:
            doc2 = fitz.open()
            w, h = fitz.paper_size("a4")
            r1 = fitz.Rect(0, 0, w, h) / 2
            r_tab = [r1, r1 + (r1.width, 0, r1.width, 0), r1 + (0, r1.height, 0, r1.height), fitz.Rect(r1.br, fitz.Rect(0, 0, w, h).br)]
            for spage in doc:
                if spage.number % 4 == 0: 
                    page = doc2.new_page(-1, width=w, height=h)
                page.show_pdf_page(r_tab[spage.number % 4], doc, spage.number)
            doc2.save(out)
            doc2.close()
        doc.close()

    def _attach_file(self, pdf_path, mode, param):
        if not os.path.exists(param): 
            raise ValueError("目标文件不存在")
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        doc = fitz.open(pdf_path)
        out = os.path.join(self._get_out_dir(pdf_path), f"{base}_已添加附件.pdf")
        
        file_data = open(param, 'rb').read()
        file_name = os.path.basename(param)
        if "页面图钉" in mode: 
            doc[0].add_file_annot(fitz.Point(50, 50), file_data, file_name)
        elif "隐藏嵌入" in mode: 
            doc.embfile_add(file_name, file_data)
        doc.save(out)
        doc.close()

    def stop(self):
        self._is_running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} —— 极简风格的PDF处理工具")
        self.active_workspace = None
        self.processed_count = 0
        self.init_ui()

    def init_ui(self):
        self.resize(1100, 760)
        
        if os.path.exists("logo.svg"):
            self.setWindowIcon(QIcon("logo.svg"))
            
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar_panel = QWidget()
        sidebar_panel.setObjectName("SidebarPanel")
        sidebar_panel.setFixedWidth(240)
        sidebar_panel.setStyleSheet("""
            QWidget#SidebarPanel {
                background-color: #090d16;
                border-right: 1px solid #1e293b;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar_panel)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        brand_container = QWidget()
        brand_container.setStyleSheet("background-color: #090d16;")
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(20, 24, 16, 16)
        brand_layout.setSpacing(12)

        logo_img_label = QLabel()
        logo_img_label.setFixedSize(32, 32)
        if os.path.exists("logo.svg"):
            logo_img_label.setPixmap(QIcon("logo.svg").pixmap(32, 32))
        else:
            logo_img_label.setText("⚡")
            logo_img_label.setStyleSheet("font-size: 24px; color: #3b82f6; background: transparent; border: none;")

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        logo_label = QLabel("QpdfTool")
        logo_label.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 800; letter-spacing: 0.5px;")
        brand_sub = QLabel("极简外观 · 全能内核")
        brand_sub.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")

        text_layout.addWidget(logo_label)
        text_layout.addWidget(brand_sub)

        brand_layout.addWidget(logo_img_label)
        brand_layout.addWidget(text_container)
        sidebar_layout.addWidget(brand_container)

        self.nav = QListWidget()
        self.nav.setObjectName("SidebarNav")
        self.nav.addItems([
            "📝 Word 与 PDF 互转",
            "📄 PDF 转图片", 
            "🖼️ 图片 转 PDF", 
            "📑 PDF 多文件合并", 
            "✂️ PDF 页码提取/删除",
            "🗜️ PDF 引擎无损压缩",
            "🔍 PDF 深度内容提取",
            "🛡️ PDF 安全与防泄漏",
            "📐 PDF 页面排版与调整",
            "📎 PDF 附件与文档嵌入"
        ])
        sidebar_layout.addWidget(self.nav)

        version_label = QLabel(f"Version {__version__}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #334155; font-size: 11px; font-weight: bold; padding: 16px; border-top: 1px solid #131b2e;")
        sidebar_layout.addWidget(version_label)

        layout.addWidget(sidebar_panel)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { background-color: #0f172a; }")

        self.ws_word = TaskWorkspace("pdf_word", "Word 与 PDF 双向转换", ['.pdf', '.docx'])
        self.ws_word.add_control(QLabel("说明: 丢入 PDF 则转出 Word；丢入 Word 则转出 PDF。"))
        self._add_action_btn(self.ws_word)
        self.stack.addWidget(self.ws_word)

        self.ws_p2i = TaskWorkspace("pdf2img", "将 PDF 拆分为单页高清图片", ['.pdf'])
        self.cb_dpi = QComboBox()
        self.cb_dpi.addItems(["72 DPI", "150 DPI (推荐)", "300 DPI", "600 DPI"])
        self.cb_dpi.setCurrentIndex(1)
        self.cb_fmt = QComboBox()
        self.cb_fmt.addItems(["PNG", "JPG"])
        self.ws_p2i.add_control(QLabel("清晰度:"))
        self.ws_p2i.add_control(self.cb_dpi)
        self.ws_p2i.add_control(QLabel("格式:"))
        self.ws_p2i.add_control(self.cb_fmt)
        self._add_action_btn(self.ws_p2i)
        self.stack.addWidget(self.ws_p2i)

        self.ws_i2p = TaskWorkspace("img2pdf", "将图片转换为 PDF 文档", ['.jpg', '.jpeg', '.png', '.webp', '.bmp'], is_sortable=True)
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["合并为一个 PDF", "分别转为独立 PDF"])
        self.ws_i2p.add_control(QLabel("模式:"))
        self.ws_i2p.add_control(self.cb_mode)
        self._add_action_btn(self.ws_i2p)
        self.stack.addWidget(self.ws_i2p)

        self.ws_merge = TaskWorkspace("pdf_merge", "将多个 PDF 合并为一个", ['.pdf'], is_sortable=True)
        self.ws_merge.add_control(QLabel("说明: 列表从上到下的顺序即为合并后的页码顺序"))
        self._add_action_btn(self.ws_merge)
        self.stack.addWidget(self.ws_merge)

        self.ws_split = TaskWorkspace("pdf_split", "提取保留 / 或安全删除指定页码", ['.pdf'])
        self.cb_split = QComboBox()
        self.cb_split.addItems(["保留选中页码", "删除选中页码"])
        self.le_split = QLineEdit()
        self.le_split.setFixedWidth(200)
        self.ws_split.setup_dynamic_input(self.cb_split, self.le_split, {"保留": "输入保留页码, 例: 1-3, 5", "删除": "输入删除页码, 例: 2, 4-6"})
        self.ws_split.add_control(self.cb_split)
        self.ws_split.add_control(self.le_split)
        self._add_action_btn(self.ws_split)
        self.stack.addWidget(self.ws_split)

        self.ws_comp = TaskWorkspace("pdf_compress", "优化并减小 PDF 文件体积", ['.pdf'])
        self.ws_comp.add_control(QLabel("说明: 使用底层深层清理算法，不影响视觉清晰度与排版"))
        self._add_action_btn(self.ws_comp)
        self.stack.addWidget(self.ws_comp)

        self.ws_ext = TaskWorkspace("pdf_extract", "解剖 PDF，提取内部元素到文件夹", ['.pdf'])
        self.cb_ext = QComboBox()
        self.cb_ext.addItems(["提取纯文本 (.txt)", "提取所有图片 (.png)", "提取表格数据 (.json)", "提取矢量图形 (.json)"])
        self.ws_ext.add_control(QLabel("提取目标:"))
        self.ws_ext.add_control(self.cb_ext)
        self._add_action_btn(self.ws_ext)
        self.stack.addWidget(self.ws_ext)

        self.ws_sec = TaskWorkspace("pdf_security", "PDF 密码管理与内容永久物理打码", ['.pdf'])
        self.cb_sec = QComboBox()
        self.cb_sec.addItems(["🔒 添加密码加密", "🔓 验证并解除密码", "⬛ 物理擦除(打黑)敏感文字"])
        self.le_sec = QLineEdit()
        self.le_sec.setFixedWidth(220)
        self.ws_sec.setup_dynamic_input(self.cb_sec, self.le_sec, {"加密": "输入要设置的密码...", "解密": "输入原密码以解密...", "擦除": "输入文档中要永久抹除的敏感词..."})
        self.ws_sec.add_control(self.cb_sec)
        self.ws_sec.add_control(self.le_sec)
        self._add_action_btn(self.ws_sec)
        self.stack.addWidget(self.ws_sec)

        self.ws_edit = TaskWorkspace("pdf_edit", "PDF 页面排版、重构与内容追加", ['.pdf'])
        self.cb_edit = QComboBox()
        self.cb_edit.addItems([
            "↻ 顺时针旋转 90°", "↺ 逆时针旋转 90°", "✂️ 统一裁剪页面", "🖼️ 添加图片水印", 
            "📄 尾部追加空白页", "📝 尾部追加文本页", "🔲 单页拆分为四页 (海报化)", "田 四页合一 (拼版打印)"
        ])
        self.le_edit = QLineEdit()
        self.le_edit.setFixedWidth(250)
        self.ws_edit.setup_dynamic_input(self.cb_edit, self.le_edit, {
            "旋转": None, "海报化": None, "合一": None, "空白页": None,
            "裁剪": "输入坐标 x0, y0, x1, y1 (例: 50,50,400,400)",
            "水印": "输入水印图片的绝对路径...",
            "文本页": "输入要在新页面写入的文字内容..."
        })
        self.ws_edit.add_control(self.cb_edit)
        self.ws_edit.add_control(self.le_edit)
        self._add_action_btn(self.ws_edit)
        self.stack.addWidget(self.ws_edit)

        self.ws_attach = TaskWorkspace("pdf_attach", "向 PDF 注入/挂载外部文件", ['.pdf'])
        self.cb_attach = QComboBox()
        self.cb_attach.addItems(["📌 以页面图钉形式附加", "📦 作为隐藏文档彻底嵌入"])
        self.le_attach = QLineEdit()
        self.le_attach.setFixedWidth(250)
        self.ws_attach.setup_dynamic_input(self.cb_attach, self.le_attach, {"图钉": "输入要附加文件的绝对路径...", "隐藏": "输入要嵌入文件的绝对路径..."})
        self.ws_attach.add_control(self.cb_attach)
        self.ws_attach.add_control(self.le_attach)
        self._add_action_btn(self.ws_attach)
        self.stack.addWidget(self.ws_attach)

        bottom_bar = QWidget()
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setStyleSheet("""
            QWidget#BottomBar {
                background-color: #090d16;
                border-top: 1px solid #1e293b;
            }
        """)
        b_layout = QHBoxLayout(bottom_bar)
        b_layout.setContentsMargins(24, 16, 24, 16)
        b_layout.setSpacing(12)

        lbl = QLabel("统一保存位置:")
        lbl.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 13px;")

        self.out_dir = QLineEdit()
        self.out_dir.setPlaceholderText("默认输出到原文件同级文件夹 (点击右侧选择)...")
        self.out_dir.setStyleSheet("""
            QLineEdit {
                background-color: #131b2e;
                border: 1px solid #1e293b;
                border-radius: 8px;
                color: #f8fafc;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)

        btn_browse = QPushButton("📁 选择输出目录")
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #3b82f6;
            }
        """)
        btn_browse.clicked.connect(lambda: self.out_dir.setText(QFileDialog.getExistingDirectory(self, "选择输出文件夹") or self.out_dir.text()))

        b_layout.addWidget(lbl)
        b_layout.addWidget(self.out_dir)
        b_layout.addWidget(btn_browse)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.stack)
        right_layout.addWidget(bottom_bar)
        
        right_container = QWidget()
        right_container.setLayout(right_layout)
        layout.addWidget(right_container, stretch=1)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

    def _add_action_btn(self, ws):
        ws.add_stretch()
        btn = QPushButton("🚀 开始处理")
        btn.setProperty("class", "action")
        btn.clicked.connect(lambda: self.run_task(ws))
        ws.add_control(btn)

    def run_task(self, ws: TaskWorkspace):
        btn = ws.control_layout.itemAt(ws.control_layout.count() - 1).widget()
        if "开始" in btn.text():
            files = ws.table.get_files()
            if not files: 
                return
            
            settings = {"out_dir": self.out_dir.text()}
            if ws.task_id == "pdf2img":
                settings["pdf_dpi"] = self.cb_dpi.currentText().split()[0]
                settings["pdf_img_fmt"] = self.cb_fmt.currentText()
            elif ws.task_id == "img2pdf":
                settings["img_pdf_mode"] = "合并" if "合并" in self.cb_mode.currentText() else "独立"
            elif ws.task_id == "pdf_split":
                settings["split_mode"] = self.cb_split.currentText()
                settings["page_range"] = self.le_split.text()
            elif ws.task_id == "pdf_extract":
                settings["ext_mode"] = self.cb_ext.currentText()
            elif ws.task_id == "pdf_security":
                settings["sec_mode"] = self.cb_sec.currentText()
                settings["sec_param"] = self.le_sec.text()
            elif ws.task_id == "pdf_edit":
                settings["edit_mode"] = self.cb_edit.currentText()
                settings["edit_param"] = self.le_edit.text()
            elif ws.task_id == "pdf_attach":
                settings["attach_mode"] = self.cb_attach.currentText()
                settings["attach_param"] = self.le_attach.text()

            btn.setText("⏹ 停止处理")
            btn.setProperty("class", "stop")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
            ws.progress_bar.setRange(0, len(files))
            ws.progress_bar.setValue(0)
            ws.progress_bar.setVisible(True)

            self.active_workspace = ws
            self.processed_count = 0
            
            self.worker = ConvertWorker(ws.task_id, files, settings)
            self.worker.progress.connect(self._on_worker_progress)
            self.worker.finished.connect(lambda c: self.task_finished(ws, btn))
            self.worker.start()
        else:
            if hasattr(self, 'worker'): 
                self.worker.stop()

    def _on_worker_progress(self, file_path, status, is_error):
        if hasattr(self, 'active_workspace') and self.active_workspace:
            self.active_workspace.table.update_status(file_path, status, is_error)
            self.processed_count += 1
            self.active_workspace.progress_bar.setValue(self.processed_count)

    def task_finished(self, ws: TaskWorkspace, btn: QPushButton):
        btn.setText("🚀 开始处理")
        btn.setProperty("class", "action")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        ws.progress_bar.setVisible(False)
        self.active_workspace = None
        
    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    app.setStyleSheet(GLOBAL_QSS)
    
    if sys.platform == "darwin":
        font = QFont("SF Pro Text", 13)
    elif sys.platform == "win32":
        font = QFont("Segoe UI", 9)
    else:
        font = QFont("Liberation Sans", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())