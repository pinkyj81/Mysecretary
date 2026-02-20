from flask import Flask, render_template, request, jsonify, redirect, url_for
from db_config import db, SQLALCHEMY_DATABASE_URI
from models import Schedule
from datetime import datetime, timedelta, time
from dotenv import load_dotenv
from sqlalchemy import inspect, text, and_, or_
import re

load_dotenv()
app = Flask(__name__)

# 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB 초기화
db.init_app(app)

SCHEDULE_TYPES = {'schedule', 'todo', 'detail', 'title'}
DEFAULT_SCHEDULE_COLOR = '#5A9FD4'
_schema_checked = False


def ensure_schedule_schema() -> None:
    global _schema_checked
    if _schema_checked:
        return

    inspector = inspect(db.engine)
    if not inspector.has_table('secretary_schedule', schema='dbo') and not inspector.has_table('secretary_schedule'):
        _schema_checked = True
        return

    try:
        columns = {column['name'].lower() for column in inspector.get_columns('secretary_schedule', schema='dbo')}
    except Exception:
        columns = {column['name'].lower() for column in inspector.get_columns('secretary_schedule')}

    if 'type' not in columns:
        db.session.execute(text("ALTER TABLE dbo.secretary_schedule ADD [type] NVARCHAR(20) NULL"))

    if 'color' not in columns:
        db.session.execute(text("ALTER TABLE dbo.secretary_schedule ADD [color] NVARCHAR(20) NULL"))

    db.session.execute(text(
        """
        UPDATE dbo.secretary_schedule
        SET [type] =
            CASE
                WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'TODO' THEN 'todo'
                WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'DETAIL' THEN 'detail'
                WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'PLAN' THEN 'schedule'
                WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[todo]%' THEN 'todo'
                WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[detail]%' THEN 'detail'
                WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[plan]%' THEN 'schedule'
                WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[schedule]%' THEN 'schedule'
                ELSE 'schedule'
            END
        WHERE [type] IS NULL OR LTRIM(RTRIM([type])) = ''
        """
    ))

    db.session.execute(text(
        """
        UPDATE dbo.secretary_schedule
        SET [color] = :default_color
        WHERE [color] IS NULL OR LTRIM(RTRIM([color])) = ''
        """
    ), {'default_color': DEFAULT_SCHEDULE_COLOR})

    db.session.commit()
    _schema_checked = True


def normalize_schedule_data(raw_description: str | None, explicit_type: str | None = None) -> tuple[str, str]:
    explicit = (explicit_type or '').strip().lower()
    if explicit == 'plan':
        explicit = 'schedule'
    if explicit in SCHEDULE_TYPES:
        return explicit, (raw_description or '').strip()

    description = (raw_description or '').strip()
    lowered = description.lower()

    for prefix, schedule_type in (
        ('[schedule]', 'schedule'),
        ('[plan]', 'schedule'),
        ('[title]', 'title'),
        ('[todo]', 'todo'),
        ('[detail]', 'detail')
    ):
        if lowered.startswith(prefix):
            return schedule_type, description[len(prefix):].strip()

    upper = description.upper()
    if upper == 'TODO':
        return 'todo', ''
    if upper == 'DETAIL':
        return 'detail', ''
    if upper == 'TITLE':
        return 'title', ''
    if upper == 'SCHEDULE':
        return 'schedule', ''
    if upper == 'PLAN':
        return 'schedule', ''

    return 'schedule', description


def serialize_description(detail: str, schedule_type: str) -> str:
    clean_detail = (detail or '').strip()
    normalized_type = schedule_type if schedule_type in SCHEDULE_TYPES else 'schedule'

    if normalized_type == 'schedule':
        return clean_detail or '계획'
    return clean_detail


def normalize_schedule_color(raw_color: str | None) -> str:
    color = (raw_color or '').strip()
    if re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        return color.upper()
    return DEFAULT_SCHEDULE_COLOR


def schedule_to_payload(schedule: Schedule) -> dict:
    payload = schedule.to_dict()
    schedule_type, clean_description = normalize_schedule_data(schedule.description, schedule.schedule_type)
    payload['schedule_type'] = schedule_type
    payload['description'] = clean_description
    return payload


@app.before_request
def ensure_schema_before_request():
    ensure_schedule_schema()

# ======================= DESKTOP 라우트 =======================

@app.route('/desktop')
def desktop_index():
    """데스크톱: 일정 목록 (캘린더 뷰)"""
    return render_template('desktop/index.html')

@app.route('/desktop/schedule')
def desktop_get_schedules():
    """데스크톱: 모든 일정 조회 (JSON)"""
    schedules = Schedule.query.order_by(Schedule.start_date.asc()).all()
    return jsonify([schedule_to_payload(s) for s in schedules])

@app.route('/desktop/schedule/<int:schedule_id>')
def desktop_get_schedule(schedule_id):
    """데스크톱: 특정 일정 조회"""
    schedule = Schedule.query.get_or_404(schedule_id)
    return jsonify(schedule_to_payload(schedule))

@app.route('/desktop/create')
def desktop_create_page():
    """데스크톱: 일정 생성 페이지"""
    return render_template('desktop/create.html')

@app.route('/desktop/weekly')
def desktop_weekly_page():
    """데스크톱: 주간 계획표 페이지"""
    return render_template('desktop/weekly.html')

@app.route('/desktop/edit/<int:schedule_id>')
def desktop_edit_page(schedule_id):
    """데스크톱: 일정 수정 페이지"""
    schedule = Schedule.query.get_or_404(schedule_id)
    return render_template('desktop/edit.html', schedule=schedule)

# ======================= MOBILE 라우트 =======================

@app.route('/mobile')
def mobile_index():
    """모바일: 일정 목록 (리스트 뷰)"""
    return render_template('mobile/index.html')

@app.route('/mobile/schedule')
def mobile_get_schedules():
    """모바일: 모든 일정 조회 (JSON)"""
    schedules = Schedule.query.order_by(Schedule.start_date.asc()).all()
    return jsonify([schedule_to_payload(s) for s in schedules])

@app.route('/mobile/schedule/<int:schedule_id>')
def mobile_get_schedule(schedule_id):
    """모바일: 특정 일정 조회"""
    schedule = Schedule.query.get_or_404(schedule_id)
    return jsonify(schedule_to_payload(schedule))

@app.route('/mobile/create')
def mobile_create_page():
    """모바일: 일정 생성 페이지"""
    return render_template('mobile/create.html')

@app.route('/mobile/edit/<int:schedule_id>')
def mobile_edit_page(schedule_id):
    """모바일: 일정 수정 페이지"""
    schedule = Schedule.query.get_or_404(schedule_id)
    return render_template('mobile/edit.html', schedule=schedule)

# ======================= CHATBOT 라우트 =======================

@app.route('/chatbot')
def chatbot_page():
    """AI 일정 비서 챗봇 페이지"""
    return render_template('chatbot.html')

# ======================= API 공통 라우트 =======================

@app.route('/api/schedule', methods=['POST'])
def create_schedule():
    """일정 생성"""
    data = request.get_json() or {}
    
    try:
        start_date = datetime.fromisoformat(data['start_date'])
        end_date = datetime.fromisoformat(data['end_date']) if data.get('end_date') else None
        
        schedule_type, clean_description = normalize_schedule_data(
            data.get('description', ''),
            data.get('schedule_type')
        )

        schedule = Schedule(
            title=data['title'],
            schedule_type=schedule_type,
            description=serialize_description(clean_description, schedule_type),
            color=normalize_schedule_color(data.get('color')),
            start_date=start_date,
            end_date=end_date,
            is_completed=False
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        return jsonify({'success': True, 'id': schedule.id, 'message': '일정이 생성되었습니다.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/schedule/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """일정 수정"""
    schedule = Schedule.query.get_or_404(schedule_id)
    data = request.get_json() or {}
    
    try:
        schedule.title = data.get('title', schedule.title)

        current_type, current_description = normalize_schedule_data(schedule.description, schedule.schedule_type)
        if 'description' in data or 'schedule_type' in data:
            input_description = data.get('description', current_description)
            input_type = data.get('schedule_type', current_type)
            next_type, next_description = normalize_schedule_data(input_description, input_type)
            schedule.schedule_type = next_type
            schedule.description = serialize_description(next_description, next_type)
        
        if 'start_date' in data:
            schedule.start_date = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data and data['end_date']:
            schedule.end_date = datetime.fromisoformat(data['end_date'])
        if 'color' in data:
            schedule.color = normalize_schedule_color(data.get('color'))
        if 'is_completed' in data:
            schedule.is_completed = data['is_completed']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '일정이 수정되었습니다.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/schedule/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """일정 삭제"""
    schedule = Schedule.query.get_or_404(schedule_id)
    
    try:
        db.session.delete(schedule)
        db.session.commit()
        return jsonify({'success': True, 'message': '일정이 삭제되었습니다.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/weekly-plan')
def weekly_plan_api():
    """주간 계획표 데이터 조회"""
    start_param = (request.args.get('start') or '').strip()
    today = datetime.now().date()

    try:
        if start_param:
            input_date = datetime.fromisoformat(start_param).date()
            week_start_date = input_date - timedelta(days=input_date.weekday())
        else:
            week_start_date = today - timedelta(days=today.weekday())
    except ValueError:
        return jsonify({'success': False, 'error': 'start 파라미터는 YYYY-MM-DD 형식이어야 합니다.'}), 400

    week_start = datetime.combine(week_start_date, time.min)
    week_end = datetime.combine(week_start_date + timedelta(days=6), time.max)

    schedules = (
        Schedule.query
        .filter(
            or_(
                and_(Schedule.start_date >= week_start, Schedule.start_date <= week_end),
                and_(Schedule.end_date.isnot(None), Schedule.start_date <= week_end, Schedule.end_date >= week_start)
            )
        )
        .order_by(Schedule.start_date.asc())
        .all()
    )

    day_keys = ['월', '화', '수', '목', '금', '토', '일']
    day_dates = [week_start_date + timedelta(days=i) for i in range(7)]
    hours = list(range(9, 23))

    title_by_day = {key: [] for key in day_keys}
    todo_by_day = {key: [] for key in day_keys}
    grid = {hour: {key: [] for key in day_keys} for hour in hours}

    for item in schedules:
        day_index = (item.start_date.date() - week_start_date).days
        if day_index < 0 or day_index > 6:
            continue

        day_key = day_keys[day_index]
        schedule_type, _ = normalize_schedule_data(item.description, item.schedule_type)

        if schedule_type == 'title':
            title_start = item.start_date.date()
            title_end = item.end_date.date() if item.end_date else title_start
            overlap_start = max(title_start, week_start_date)
            overlap_end = min(title_end, week_start_date + timedelta(days=6))

            if overlap_start > overlap_end:
                continue

            for offset in range((overlap_end - overlap_start).days + 1):
                current_date = overlap_start + timedelta(days=offset)
                current_key = day_keys[(current_date - week_start_date).days]
                title_by_day[current_key].append({
                    'id': item.id,
                    'title': item.title,
                    'color': item.color,
                    'is_completed': bool(item.is_completed)
                })
            continue

        if schedule_type == 'todo':
            todo_by_day[day_key].append({
                'id': item.id,
                'time': None,
                'title': item.title,
                'is_completed': bool(item.is_completed)
            })
            continue

        if schedule_type != 'schedule':
            continue

        hour = item.start_date.hour
        minute_text = f"{item.start_date.minute:02d}"

        if hour in grid:
            label = item.title if item.start_date.minute == 0 else f"{hour}:{minute_text} {item.title}"
            if item.start_date.minute == 0:
                grid[hour][day_key].append({
                    'id': item.id,
                    'title': item.title,
                    'label': label,
                    'is_completed': bool(item.is_completed)
                })
            else:
                grid[hour][day_key].append({
                    'id': item.id,
                    'title': item.title,
                    'label': label,
                    'is_completed': bool(item.is_completed)
                })

    return jsonify({
        'success': True,
        'week_start': week_start_date.strftime('%Y-%m-%d'),
        'week_end': (week_start_date + timedelta(days=6)).strftime('%Y-%m-%d'),
        'days': [
            {'label': day_keys[i], 'date': day_dates[i].strftime('%m-%d')}
            for i in range(7)
        ],
        'hours': hours,
        'title_by_day': title_by_day,
        'todo_by_day': todo_by_day,
        'grid': grid
    })

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """규칙 기반 챗봇 메시지 처리 및 일정 생성"""
    data = request.get_json() or {}
    message = (data.get('message') or '').strip()

    if not message:
        return jsonify({'success': False, 'error': '메시지가 비어 있습니다.'}), 400

    def is_create_request(text: str) -> bool:
        create_keywords = ('추가', '등록', '예약', '잡아', '넣어', '만들어', '생성')
        return any(keyword in text for keyword in create_keywords)

    def is_weekly_template_request(text: str) -> bool:
        weekly_keywords = ('주간 계획표', '주간계획표', '주간 템플릿', '주간템플릿')
        return any(keyword in text for keyword in weekly_keywords) and is_create_request(text)

    def is_query_request(text: str) -> bool:
        create_keywords = ('추가', '등록', '예약', '잡아', '넣어', '만들어', '생성')
        query_keywords = (
            '조회', '보여', '알려', '있어', '뭐야', '뭐 있어', '확인', '보고', '찾아'
        )
        if any(keyword in text for keyword in create_keywords):
            return False
        if '일정' in text or '스케줄' in text:
            return True
        return any(keyword in text for keyword in query_keywords)

    def parse_date_range(text: str) -> tuple[datetime, datetime]:
        today_date = datetime.now().date()
        start_date = None
        end_date = None

        if '오늘' in text:
            start_date = today_date
            end_date = today_date
        elif '내일' in text:
            start_date = today_date + timedelta(days=1)
            end_date = start_date
        elif '모레' in text:
            start_date = today_date + timedelta(days=2)
            end_date = start_date
        elif '이번주' in text or '이번 주' in text:
            start_date = today_date - timedelta(days=today_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif '다음주' in text or '다음 주' in text:
            start_date = today_date - timedelta(days=today_date.weekday()) + timedelta(days=7)
            end_date = start_date + timedelta(days=6)
        elif '지난주' in text or '지난 주' in text:
            start_date = today_date - timedelta(days=today_date.weekday()) - timedelta(days=7)
            end_date = start_date + timedelta(days=6)
        elif '이번달' in text or '이번 달' in text:
            start_date = today_date.replace(day=1)
            next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_month - timedelta(days=1)

        date_matches = re.findall(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
        parsed_dates = []
        for year, month, day in date_matches:
            try:
                parsed_dates.append(datetime(int(year), int(month), int(day)).date())
            except ValueError:
                continue

        if len(parsed_dates) >= 2:
            start_date = parsed_dates[0]
            end_date = parsed_dates[1]
        elif len(parsed_dates) == 1:
            start_date = parsed_dates[0]
            end_date = parsed_dates[0]

        if start_date is None or end_date is None:
            start_date = today_date - timedelta(days=today_date.weekday())
            end_date = start_date + timedelta(days=6)

        range_start = datetime.combine(start_date, time.min)
        range_end = datetime.combine(end_date, time.max)
        return range_start, range_end

    def parse_target_datetime(text: str) -> datetime:
        now = datetime.now()
        target_date = now.date()

        date_match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
        if date_match:
            year, month, day = map(int, date_match.groups())
            target_date = datetime(year, month, day).date()
        elif '내일' in text:
            target_date = target_date + timedelta(days=1)
        elif '모레' in text:
            target_date = target_date + timedelta(days=2)
        elif '오늘' in text:
            target_date = target_date

        hour = 9
        minute = 0

        hm_match = re.search(r'(?<!\d)(\d{1,2}):(\d{2})(?!\d)', text)
        if hm_match:
            hour, minute = map(int, hm_match.groups())
        else:
            ap_match = re.search(r'(오전|오후)\s*(\d{1,2})시(?:\s*(\d{1,2})분?)?', text)
            if ap_match:
                ampm, h, m = ap_match.groups()
                hour = int(h) % 12
                if ampm == '오후':
                    hour += 12
                minute = int(m) if m else 0
            else:
                h_match = re.search(r'(?<!\d)(\d{1,2})시(?:\s*(\d{1,2})분?)?', text)
                if h_match:
                    h, m = h_match.groups()
                    hour = int(h)
                    minute = int(m) if m else 0

        if '저녁' in text and hour < 12:
            hour += 12

        return datetime.combine(target_date, time(hour=hour, minute=minute))

    def resolve_week_start(text: str) -> datetime:
        today = datetime.now().date()

        date_match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
        if date_match:
            year, month, day = map(int, date_match.groups())
            target = datetime(year, month, day).date()
            monday = target - timedelta(days=target.weekday())
            return datetime.combine(monday, time.min)

        current_monday = today - timedelta(days=today.weekday())
        if '다음주' in text or '다음 주' in text:
            current_monday = current_monday + timedelta(days=7)
        elif '지난주' in text or '지난 주' in text:
            current_monday = current_monday - timedelta(days=7)

        return datetime.combine(current_monday, time.min)

    def extract_title(text: str) -> str:
        quoted = re.search(r'"([^"]+)"|\'([^\']+)\'', text)
        if quoted:
            return (quoted.group(1) or quoted.group(2) or '').strip()

        cleaned = text
        cleaned = re.sub(r'\d{4}[-/.]\d{1,2}[-/.]\d{1,2}', ' ', cleaned)
        cleaned = re.sub(r'\d{1,2}:\d{2}', ' ', cleaned)
        cleaned = re.sub(r'(오전|오후)\s*\d{1,2}시\s*\d{0,2}분?', ' ', cleaned)
        cleaned = re.sub(r'\d{1,2}시\s*\d{0,2}분?', ' ', cleaned)
        cleaned = re.sub(r'(오늘|내일|모레|저녁|오전|오후)', ' ', cleaned)

        for keyword in (
            '일정', '스케줄', '추가', '등록', '예약', '잡아줘', '잡아',
            '넣어줘', '넣어', '만들어줘', '만들어', '생성', '해줘', '해주세요'
        ):
            cleaned = cleaned.replace(keyword, ' ')

        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .,!?-')
        return cleaned or '새 일정'

    if is_weekly_template_request(message):
        try:
            week_start = resolve_week_start(message)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            existing_templates = (
                Schedule.query
                .filter(Schedule.start_date >= week_start)
                .filter(Schedule.start_date <= week_end)
                .filter(Schedule.title.like('주간 계획 (%)'))
                .all()
            )

            existing_dates = {item.start_date.date() for item in existing_templates}
            weekday_labels = ['월', '화', '수', '목', '금', '토', '일']
            created_count = 0

            for offset, label in enumerate(weekday_labels):
                day = (week_start + timedelta(days=offset)).date()
                if day in existing_dates:
                    continue

                schedule = Schedule(
                    title=f'주간 계획 ({label})',
                    schedule_type='schedule',
                    description='주간 계획 템플릿',
                    start_date=datetime.combine(day, time(hour=9, minute=0)),
                    end_date=None,
                    is_completed=False
                )
                db.session.add(schedule)
                created_count += 1

            db.session.commit()

            period_text = f"{week_start.strftime('%Y-%m-%d')} ~ {(week_start + timedelta(days=6)).strftime('%Y-%m-%d')}"
            if created_count == 0:
                return jsonify({'success': True, 'message': f'이미 해당 주차 템플릿이 있습니다. ({period_text})'})

            return jsonify({'success': True, 'message': f'주간 계획표 템플릿 {created_count}건을 생성했습니다. ({period_text})'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    if is_query_request(message):
        range_start, range_end = parse_date_range(message)

        schedules = (
            Schedule.query
            .filter(Schedule.start_date >= range_start)
            .filter(Schedule.start_date <= range_end)
            .order_by(Schedule.start_date.asc())
            .all()
        )

        if not schedules:
            return jsonify({'success': True, 'message': '요청하신 기간에 일정이 없습니다.'})

        lines = ['요청하신 기간의 일정입니다:']
        for schedule in schedules:
            when = schedule.start_date.strftime('%m-%d %H:%M')
            lines.append(f"- {when} {schedule.title}")

        return jsonify({'success': True, 'message': "\n".join(lines)})

    if not is_create_request(message):
        return jsonify({
            'success': True,
            'message': '일정 생성은 "내일 오후 3시 회의 일정 추가"처럼 말해 주세요.'
        })

    try:
        start_date = parse_target_datetime(message)
        title = extract_title(message)

        schedule = Schedule(
            title=title,
            schedule_type='schedule',
            description='계획',
            start_date=start_date,
            end_date=None,
            is_completed=False
        )

        db.session.add(schedule)
        db.session.commit()

        when = start_date.strftime('%Y-%m-%d %H:%M')
        return jsonify({'success': True, 'message': f'일정을 등록했어요: {when} {title}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat/models')
def chat_models():
    """규칙 기반 모드 안내"""
    return jsonify({
        'success': True,
        'mode': 'rule-based',
        'models': []
    })

@app.route('/')
def index():
    """홈 페이지 - 모바일/데스크톱 선택"""
    return redirect(url_for('desktop_index'))

# ======================= 에러 핸들러 =======================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            ensure_schedule_schema()
            print("✅ MSSQL yujincast 데이터베이스 테이블 초기화 완료")
            print("📊 테이블명: secretary_schedule")
        except Exception as e:
            print(f"❌ 데이터베이스 초기화 오류: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
