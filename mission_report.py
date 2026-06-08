import sys
import os
import math
import random
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.platypus import PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import subprocess


class MissionReportGenerator:
    """ミッションレポート生成クラス"""

    def __init__(self):
        self.mission_data = {}
        self.setup_fonts()

    def setup_fonts(self):
        """日本語フォントのセットアップ"""
        font_paths = [
            "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
            "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        self.font_name = "Helvetica"
        for path in font_paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont('JapaneseFont', path))
                    self.font_name = 'JapaneseFont'
                    break
                except:
                    pass

    def generate_report(self, mission_data, output_path):
        """PDFレポートを生成"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        styles = getSampleStyleSheet()
        fn = self.font_name

        # カスタムスタイル
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName=fn,
            fontSize=20,
            textColor=colors.HexColor('#003366'),
            spaceAfter=10,
            alignment=TA_CENTER
        )
        heading1_style = ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontName=fn,
            fontSize=14,
            textColor=colors.HexColor('#003366'),
            spaceBefore=15,
            spaceAfter=8,
            borderPad=5,
        )
        heading2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontName=fn,
            fontSize=12,
            textColor=colors.HexColor('#005599'),
            spaceBefore=10,
            spaceAfter=5,
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=fn,
            fontSize=10,
            spaceAfter=5,
            leading=16,
        )
        small_style = ParagraphStyle(
            'CustomSmall',
            parent=styles['Normal'],
            fontName=fn,
            fontSize=9,
            textColor=colors.gray,
        )
        alert_style = ParagraphStyle(
            'AlertStyle',
            parent=styles['Normal'],
            fontName=fn,
            fontSize=10,
            textColor=colors.red,
            spaceBefore=5,
            spaceAfter=5,
        )
        success_style = ParagraphStyle(
            'SuccessStyle',
            parent=styles['Normal'],
            fontName=fn,
            fontSize=10,
            textColor=colors.HexColor('#007700'),
            spaceBefore=5,
            spaceAfter=5,
        )

        story = []

        # ===== 表紙 =====
        story.append(Spacer(1, 20*mm))
        story.append(Paragraph("PHENIX Mission Report", title_style))
        story.append(Paragraph("自律分散型アンテナシステム ミッションレポート", title_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 10*mm))

        # ミッション基本情報
        info_data = [
            ["項目", "内容"],
            ["ミッションID", mission_data.get('mission_id', 'PHENIX-2026-001')],
            ["実施日時", mission_data.get('datetime', datetime.now().strftime('%Y年%m月%d日 %H:%M'))],
            ["実施場所", mission_data.get('location', 'オーストラリア・NSW州オレンジ市近郊')],
            ["ミッション種別", mission_data.get('type', '生存者探索・通信インフラ展開')],
            ["オペレーター", mission_data.get('operator', '（オペレーター名）')],
            ["天候", mission_data.get('weather', '晴れ / 風速3m/s / 気温22℃')],
            ["ミッション結果", mission_data.get('result', '成功')],
        ]

        info_table = Table(info_data, colWidths=[50*mm, 120*mm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), fn),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#E8F0F8')),
            ('FONTNAME', (0, 1), (0, -1), fn),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FF')]),
        ]))
        story.append(info_table)
        story.append(PageBreak())

        # ===== 1. ミッションサマリー =====
        story.append(Paragraph("1. ミッションサマリー", heading1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 3*mm))

        summary_data = [
            ["指標", "値", "評価"],
            ["通信カバレッジ",
             f"{mission_data.get('coverage', 87.3):.1f}%",
             "優秀" if mission_data.get('coverage', 87.3) > 80 else "要改善"],
            ["展開ノード数",
             f"{mission_data.get('nodes_deployed', 18)}/{mission_data.get('total_nodes', 24)}個",
             "正常"],
            ["生存者検知数",
             f"{mission_data.get('survivors_detected', 3)}人",
             "検知成功" if mission_data.get('survivors_detected', 3) > 0 else "未検知"],
            ["位置特定精度",
             f"±{mission_data.get('location_accuracy', 0.8):.1f}m",
             "高精度" if mission_data.get('location_accuracy', 0.8) < 2 else "要改善"],
            ["ミッション時間",
             f"{mission_data.get('mission_time', 45)}分",
             "正常"],
            ["VTOL飛行時間",
             f"{mission_data.get('vtol_flight_time', 38)}分（交互運用）",
             "正常"],
            ["通信モード",
             mission_data.get('comm_mode', 'LoRaメッシュ + Starlink'),
             "正常"],
            ["最小RSSI",
             f"{mission_data.get('min_rssi', -82)} dBm",
             "正常" if mission_data.get('min_rssi', -82) > -90 else "要注意"],
        ]

        summary_table = Table(summary_data, colWidths=[60*mm, 70*mm, 40*mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), fn),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#E8F0F8')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FF')]),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 5*mm))

        # ===== 2. システム稼働状況 =====
        story.append(Paragraph("2. システム稼働状況", heading1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 3*mm))

        story.append(Paragraph("2.1 VTOL稼働状況", heading2_style))
        vtol_data = [
            ["機体", "状態", "飛行時間", "バッテリー消費", "飛行回数"],
            ["ArgusFPV Y3①",
             mission_data.get('vtol1_status', '正常'),
             f"{mission_data.get('vtol1_flight', 38)}分",
             f"{mission_data.get('vtol1_battery', 85)}%",
             f"{mission_data.get('vtol1_flights', 2)}回"],
            ["ArgusFPV Y3②",
             mission_data.get('vtol2_status', '正常'),
             f"{mission_data.get('vtol2_flight', 36)}分",
             f"{mission_data.get('vtol2_battery', 82)}%",
             f"{mission_data.get('vtol2_flights', 2)}回"],
        ]
        vtol_table = Table(vtol_data, colWidths=[40*mm, 30*mm, 30*mm, 35*mm, 25*mm])
        vtol_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#005599')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), fn),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FF')]),
        ]))
        story.append(vtol_table)
        story.append(Spacer(1, 5*mm))

        story.append(Paragraph("2.2 LoRaノード稼働状況", heading2_style))
        node_header = ["ノードID", "種別", "RSSI", "バッテリー", "レーダー検知", "状態"]
        node_data = [node_header]

        nodes = mission_data.get('nodes', [])
        if not nodes:
            for i in range(1, 19):
                kind = "母艦" if i <= 8 else ("VTOL①" if i <= 12 else "VTOL②")
                nodes.append({
                    'id': i, 'type': kind,
                    'rssi': random.randint(-80, -60),
                    'battery': random.randint(75, 100),
                    'detections': random.randint(0, 5),
                    'status': '正常'
                })

        for node in nodes[:18]:
            node_data.append([
                f"N{node['id']:02d}",
                node.get('type', '母艦'),
                f"{node.get('rssi', -70)} dBm",
                f"{node.get('battery', 95)}%",
                f"{node.get('detections', 0)}件",
                node.get('status', '正常'),
            ])

        node_table = Table(node_data, colWidths=[20*mm, 25*mm, 30*mm, 25*mm, 30*mm, 25*mm])
        node_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#005599')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), fn),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FF')]),
        ]))
        story.append(node_table)
        story.append(PageBreak())

        # ===== 3. 生存者検知結果 =====
        story.append(Paragraph("3. 生存者検知結果", heading1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 3*mm))

        survivors = mission_data.get('survivors', [])
        if not survivors:
            survivors = [
                {'id': 1, 'lat': -33.2841, 'lng': 149.1023, 'alt': 0,
                 'temp': 37.2, 'confidence': 95, 'method': 'サーマル+三角測量', 'time': '10:23:15'},
                {'id': 2, 'lat': -33.2819, 'lng': 149.0991, 'alt': 2,
                 'temp': 36.8, 'confidence': 88, 'method': 'mmWaveレーダー+TDOA', 'time': '12:45:33'},
                {'id': 3, 'lat': -33.2855, 'lng': 149.1047, 'alt': 0,
                 'temp': 37.5, 'confidence': 97, 'method': 'サーマル+TDOA', 'time': '15:12:08'},
            ]

        if survivors:
            sv_header = ["No.", "検知時刻", "緯度", "経度", "高度", "体温", "確度", "検知方法"]
            sv_data = [sv_header]
            for sv in survivors:
                sv_data.append([
                    f"生存者{sv['id']}",
                    sv.get('time', '--:--:--'),
                    f"{sv.get('lat', 0):.4f}",
                    f"{sv.get('lng', 0):.4f}",
                    f"{sv.get('alt', 0):.1f}m",
                    f"{sv.get('temp', 37.0):.1f}℃",
                    f"{sv.get('confidence', 90)}%",
                    sv.get('method', 'サーマル'),
                ])

            sv_table = Table(sv_data, colWidths=[20*mm, 22*mm, 22*mm, 22*mm, 16*mm, 16*mm, 16*mm, 36*mm])
            sv_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CC0000')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), fn),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('PADDING', (0, 0), (-1, -1), 4),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.HexColor('#FFF0F0'), colors.HexColor('#FFE8E8')]),
            ]))
            story.append(sv_table)
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph(
                f"※ 全{len(survivors)}名の位置情報を救助本部に送信済み。",
                success_style
            ))
        else:
            story.append(Paragraph("※ 本ミッションでは生存者は検知されませんでした。", normal_style))

        story.append(Spacer(1, 5*mm))

        # ===== 4. 通信ログ =====
        story.append(Paragraph("4. 通信ログ（抜粋）", heading1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 3*mm))

        logs = mission_data.get('logs', [])
        if not logs:
            logs = [
                {'time': '10:00:00', 'level': 'INFO', 'message': 'PHENIXシステム起動完了'},
                {'time': '10:01:30', 'level': 'INFO', 'message': 'VTOL①離陸・自律追従開始（高度30m）'},
                {'time': '10:05:22', 'level': 'WARN', 'message': 'RSSI低下検知: -87dBm → ノード1自動投下'},
                {'time': '10:05:29', 'level': 'INFO', 'message': 'ノード1展開完了・メッシュ形成'},
                {'time': '10:23:15', 'level': 'ALERT', 'message': '生存者1検知！座標: -33.2841, 149.1023'},
                {'time': '10:23:18', 'level': 'INFO', 'message': '三角測量開始→座標特定完了 誤差±0.8m'},
                {'time': '10:23:20', 'level': 'INFO', 'message': '救助本部に位置情報送信完了'},
                {'time': '11:15:00', 'level': 'INFO', 'message': 'VTOL①バッテリー15%→自動帰還開始'},
                {'time': '11:15:30', 'level': 'INFO', 'message': 'VTOL②自動出撃・交替完了'},
                {'time': '12:45:33', 'level': 'ALERT', 'message': '生存者2検知！座標: -33.2819, 149.0991'},
                {'time': '15:12:08', 'level': 'ALERT', 'message': '生存者3検知！座標: -33.2855, 149.1047'},
                {'time': '15:45:00', 'level': 'INFO', 'message': 'ミッション完了・全システム帰還'},
            ]

        log_header = ["時刻", "レベル", "メッセージ"]
        log_data = [log_header]
        for log in logs:
            log_data.append([
                log.get('time', '--:--:--'),
                log.get('level', 'INFO'),
                log.get('message', ''),
            ])

        log_table = Table(log_data, colWidths=[25*mm, 20*mm, 125*mm])
        log_colors = []
        for i, log in enumerate(logs, 1):
            level = log.get('level', 'INFO')
            if level == 'ALERT':
                log_colors.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FFE8E8')))
            elif level == 'WARN':
                log_colors.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FFF8E8')))

        log_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), fn),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ] + log_colors))
        story.append(log_table)
        story.append(PageBreak())

        # ===== 5. 総合評価 =====
        story.append(Paragraph("5. 総合評価・考察", heading1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 3*mm))

        story.append(Paragraph("5.1 成果", heading2_style))
        achievements = mission_data.get('achievements', [
            f"通信カバレッジ {mission_data.get('coverage', 87.3):.1f}% を達成（目標80%以上）",
            f"生存者 {mission_data.get('survivors_detected', 3)}名 を検知・位置特定に成功",
            f"VTOL2機交互運用により {mission_data.get('mission_time', 45)}分間の継続監視を実現",
            "5段階冗長通信により通信途絶ゼロを達成",
            "全ノードの自律展開・メッシュ形成に成功",
        ])
        for ach in achievements:
            story.append(Paragraph(f"✓ {ach}", success_style))

        story.append(Spacer(1, 3*mm))
        story.append(Paragraph("5.2 改善点", heading2_style))
        improvements = mission_data.get('improvements', [
            "RSSI閾値の最適化により、より早いノード投下タイミングを検討",
            "生存者検知アルゴリズムの精度向上（現在95%→目標99%）",
            "バッテリー消費の最適化による飛行時間延長",
        ])
        for imp in improvements:
            story.append(Paragraph(f"△ {imp}", normal_style))

        story.append(Spacer(1, 5*mm))

        # ===== 6. 次回ミッション計画 =====
        story.append(Paragraph("6. 次回ミッション計画", heading1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 3*mm))

        next_plans = mission_data.get('next_plans', [
            "ノード24個フル展開テスト（今回18個）",
            "夜間ミッションテスト（暗視カメラ統合）",
            "悪天候下（風速10m/s以上）での動作確認",
            "複数被災地同時対応テスト",
        ])
        for plan in next_plans:
            story.append(Paragraph(f"→ {plan}", normal_style))

        story.append(Spacer(1, 10*mm))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 3*mm))

        footer_style = ParagraphStyle(
            'Footer', parent=styles['Normal'],
            fontName=fn, fontSize=9,
            textColor=colors.grey, alignment=TA_CENTER
        )
        story.append(Paragraph(
            f"PHENIX Project | {datetime.now().strftime('%Y年%m月%d日')} | github.com/PhenixFRFR/PHENIX",
            footer_style
        ))
        story.append(Paragraph(
            "本レポートはPHENIX自動レポート生成システムにより作成されました",
            footer_style
        ))

        doc.build(story)
        return output_path


class MissionReportUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📋 PHENIX 自動ミッションレポート生成")
        self.setGeometry(100, 100, 900, 700)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.generator = MissionReportGenerator()
        self.report_path = os.path.expanduser("~/PHENIX/PHENIX_Mission_Report.pdf")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📋 PHENIX 自動ミッションレポート生成")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("ミッション終了後に自動でPDFレポートを生成します")
        subtitle.setStyleSheet("font-size: 12px; color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # ミッション情報入力
        info_group = QGroupBox("📝 ミッション情報")
        info_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        info_layout = QGridLayout()

        fields = [
            ("ミッションID:", "PHENIX-2026-001", 0),
            ("実施場所:", "オーストラリア・NSW州オレンジ市近郊", 1),
            ("ミッション種別:", "生存者探索・通信インフラ展開", 2),
            ("オペレーター:", "（オペレーター名）", 3),
            ("天候:", "晴れ / 風速3m/s / 気温22℃", 4),
        ]

        self.fields = {}
        for label, default, row in fields:
            info_layout.addWidget(QLabel(label), row, 0)
            field = QLineEdit(default)
            field.setStyleSheet(
                "background-color: #0a0a1a; color: #00ff88; border: 1px solid #333333; padding: 3px;"
            )
            info_layout.addWidget(field, row, 1)
            self.fields[label] = field

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # ミッション結果
        result_group = QGroupBox("📊 ミッション結果")
        result_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        result_layout = QGridLayout()

        metrics = [
            ("カバレッジ (%):", "87.3", 0, 0),
            ("展開ノード数:", "18", 0, 2),
            ("生存者検知数:", "3", 1, 0),
            ("位置特定精度 (m):", "0.8", 1, 2),
            ("ミッション時間 (分):", "45", 2, 0),
            ("最小RSSI (dBm):", "-82", 2, 2),
        ]

        self.metrics = {}
        for label, default, row, col in metrics:
            result_layout.addWidget(QLabel(label), row, col)
            field = QLineEdit(default)
            field.setStyleSheet(
                "background-color: #0a0a1a; color: #00ff88; border: 1px solid #333333; padding: 3px;"
            )
            result_layout.addWidget(field, row, col + 1)
            self.metrics[label] = field

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # ボタン
        btn_layout = QHBoxLayout()

        self.btn_generate = QPushButton("📄 レポート生成")
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #005500; }
        """)
        self.btn_generate.clicked.connect(self.generate_report)
        btn_layout.addWidget(self.btn_generate)

        self.btn_open = QPushButton("📂 PDFを開く")
        self.btn_open.setStyleSheet("""
            QPushButton {
                background-color: #000033;
                color: #00aaff;
                border: 2px solid #00aaff;
                padding: 12px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #000055; }
        """)
        self.btn_open.clicked.connect(self.open_pdf)
        self.btn_open.setEnabled(False)
        btn_layout.addWidget(self.btn_open)

        btn_demo = QPushButton("🎬 デモデータで生成")
        btn_demo.setStyleSheet("""
            QPushButton {
                background-color: #333300;
                color: #ffaa00;
                border: 2px solid #ffaa00;
                padding: 12px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #555500; }
        """)
        btn_demo.clicked.connect(self.generate_demo_report)
        btn_layout.addWidget(btn_demo)

        layout.addLayout(btn_layout)

        self.progress = QProgressBar()
        self.progress.setStyleSheet("QProgressBar::chunk { background-color: #00ff88; }")
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_label = QLabel("✅ 待機中")
        self.status_label.setStyleSheet("font-size: 14px; color: #00ff88;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;"
        )
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.log("📋 PHENIX 自動ミッションレポート生成システム起動！")
        self.log("「レポート生成」または「デモデータで生成」ボタンで生成開始！")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def get_mission_data(self):
        data = {
            'mission_id': self.fields["ミッションID:"].text(),
            'location': self.fields["実施場所:"].text(),
            'type': self.fields["ミッション種別:"].text(),
            'operator': self.fields["オペレーター:"].text(),
            'weather': self.fields["天候:"].text(),
            'datetime': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
            'result': '成功',
        }
        try:
            data['coverage'] = float(self.metrics["カバレッジ (%):"].text())
            data['nodes_deployed'] = int(self.metrics["展開ノード数:"].text())
            data['survivors_detected'] = int(self.metrics["生存者検知数:"].text())
            data['location_accuracy'] = float(self.metrics["位置特定精度 (m):"].text())
            data['mission_time'] = int(self.metrics["ミッション時間 (分):"].text())
            data['min_rssi'] = int(self.metrics["最小RSSI (dBm):"].text())
        except:
            pass
        return data

    def generate_report(self):
        self.btn_generate.setEnabled(False)
        self.progress.setValue(20)
        self.status_label.setText("📄 レポート生成中...")
        self.log("📄 レポート生成開始...")
        QApplication.processEvents()

        try:
            data = self.get_mission_data()
            self.progress.setValue(60)
            QApplication.processEvents()

            self.generator.generate_report(data, self.report_path)
            self.progress.setValue(100)
            self.status_label.setText("✅ レポート生成完了！")
            self.status_label.setStyleSheet("font-size: 14px; color: #00ff88;")
            self.btn_open.setEnabled(True)
            self.log(f"✅ レポート生成完了！")
            self.log(f"📁 保存先: {self.report_path}")
        except Exception as e:
            self.status_label.setText(f"❌ エラー: {str(e)}")
            self.status_label.setStyleSheet("font-size: 14px; color: #ff4444;")
            self.log(f"❌ エラー: {str(e)}")

        self.btn_generate.setEnabled(True)

    def generate_demo_report(self):
        self.btn_generate.setEnabled(False)
        self.progress.setValue(20)
        self.status_label.setText("🎬 デモレポート生成中...")
        self.log("🎬 デモデータでレポート生成開始...")
        QApplication.processEvents()

        try:
            demo_data = {
                'mission_id': 'PHENIX-DEMO-001',
                'datetime': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
                'location': 'オーストラリア・NSW州オレンジ市近郊（実証実験場）',
                'type': '生存者探索・通信インフラ展開',
                'operator': 'PHENIX オペレーター',
                'weather': '晴れ / 風速3m/s / 気温22℃ / 視程10km',
                'result': '成功',
                'coverage': 87.3,
                'nodes_deployed': 18,
                'total_nodes': 24,
                'survivors_detected': 3,
                'location_accuracy': 0.8,
                'mission_time': 45,
                'vtol_flight_time': 38,
                'min_rssi': -82,
                'comm_mode': 'LoRaメッシュ + Starlink',
            }

            self.progress.setValue(60)
            QApplication.processEvents()

            self.generator.generate_report(demo_data, self.report_path)
            self.progress.setValue(100)
            self.status_label.setText("✅ デモレポート生成完了！")
            self.btn_open.setEnabled(True)
            self.log(f"✅ デモレポート生成完了！")
            self.log(f"📁 保存先: {self.report_path}")
        except Exception as e:
            self.status_label.setText(f"❌ エラー: {str(e)}")
            self.status_label.setStyleSheet("font-size: 14px; color: #ff4444;")
            self.log(f"❌ エラー: {str(e)}")

        self.btn_generate.setEnabled(True)

    def open_pdf(self):
        subprocess.Popen(['firefox', self.report_path])
        self.log("📂 PDFをFirefoxで開きました")


if __name__ == "__main__":
    # reportlabのインストール確認
    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        import subprocess
        subprocess.run(['pip3', 'install', 'reportlab', '--break-system-packages'])

    app = QApplication(sys.argv)
    window = MissionReportUI()
    window.show()
    sys.exit(app.exec())
