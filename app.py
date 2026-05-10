from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from db_config import db, SQLALCHEMY_DATABASE_URI
from models import Schedule, Routine, User, ColorPreset
from datetime import datetime, timedelta, time, date
from dotenv import load_dotenv
from sqlalchemy import inspect, text, and_, or_
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import re
import os
import calendar

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecretary-dev-key')

# 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB 초기화
db.init_app(app)

SCHEDULE_TYPES = {'schedule', 'todo', 'detail', 'title', 'routine'}
DEFAULT_SCHEDULE_COLOR = '#5A9FD4'
DEFAULT_COLOR_PRESETS = [
    {'name': '개인 일정', 'color': '#F472B6'},
    {'name': '큰애 일정', 'color': '#1E3A8A'},
    {'name': '작은애 일정', 'color': '#0EA5E9'},
    {'name': '가족 일정', 'color': '#10B981'},
]
_schema_checked = False
KIDS_SCHEDULE_FOLDER = os.path.join(app.root_path, 'static', 'kids_schedule')
KIDS_SCHEDULE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
PUBLIC_ENDPOINTS = {'login_page', 'logout', 'static'}

os.makedirs(KIDS_SCHEDULE_FOLDER, exist_ok=True)


def is_allowed_kids_schedule_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in KIDS_SCHEDULE_EXTENSIONS


def get_default_user() -> User:
    username = 'admin'
    password = '1234'

    user = User.query.filter(User.username == username).first()
    if user:
        if not check_password_hash(user.password_hash, password):
            user.password_hash = generate_password_hash(password)
            db.session.commit()
        return user

    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return user


def current_user_id() -> int | None:
    user_id = session.get('user_id')
    if not user_id:
        return None
    try:
        return int(user_id)
    except Exception:
        return None


def get_my_schedule_or_404(schedule_id: int) -> Schedule:
    user_id = current_user_id()
    return (
        Schedule.query
        .filter(Schedule.id == schedule_id, Schedule.user_id == user_id)
        .first_or_404()
    )


def get_my_routine_or_404(routine_id: int) -> Routine:
    user_id = current_user_id()
    return (
        Routine.query
        .filter(Routine.id == routine_id, Routine.user_id == user_id)
        .first_or_404()
    )


def get_my_color_preset_or_404(preset_id: int) -> ColorPreset:
    user_id = current_user_id()
    return (
        ColorPreset.query
        .filter(ColorPreset.id == preset_id, ColorPreset.user_id == user_id)
        .first_or_404()
    )


def ensure_user_color_presets(user_id: int | None) -> None:
    if not user_id:
        return

    exists = (
        ColorPreset.query
        .filter(ColorPreset.user_id == user_id)
        .first()
    )
    if exists:
        return

    for idx, item in enumerate(DEFAULT_COLOR_PRESETS):
        db.session.add(ColorPreset(
            user_id=user_id,
            name=item['name'],
            color=normalize_schedule_color(item['color']),
            sort_order=idx,
        ))
    db.session.commit()


def ensure_schedule_schema() -> None:
    global _schema_checked
    if _schema_checked:
        return

    inspector = inspect(db.engine)

    try:
        db.create_all()
    except Exception:
        pass

    default_user = None
    try:
        default_user = get_default_user()
        ensure_user_color_presets(default_user.id)
    except Exception:
        default_user = None

    has_table = False
    try:
        has_table = inspector.has_table('secretary_schedule', schema='dbo')
    except Exception:
        has_table = False
    if not has_table:
        has_table = inspector.has_table('secretary_schedule')

    if not has_table:
        _schema_checked = True
        return

    try:
        try:
            columns = {column['name'].lower() for column in inspector.get_columns('secretary_schedule', schema='dbo')}
            table_ref = 'dbo.secretary_schedule'
        except Exception:
            columns = {column['name'].lower() for column in inspector.get_columns('secretary_schedule')}
            table_ref = 'secretary_schedule'

        if 'type' not in columns:
            db.session.execute(text(f"ALTER TABLE {table_ref} ADD [type] NVARCHAR(20) NULL"))

        if 'color' not in columns:
            db.session.execute(text(f"ALTER TABLE {table_ref} ADD [color] NVARCHAR(20) NULL"))

        if 'user_id' not in columns:
            db.session.execute(text(f"ALTER TABLE {table_ref} ADD [user_id] INT NULL"))

        db.session.execute(text(
            f"""
            UPDATE {table_ref}
            SET [type] =
                CASE
                    WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'TODO' THEN 'todo'
                    WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'DETAIL' THEN 'detail'
                    WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'PLAN' THEN 'schedule'
                    WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[todo]%' THEN 'todo'
                    WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[detail]%' THEN 'detail'
                    WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[plan]%' THEN 'schedule'
                    WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[schedule]%' THEN 'schedule'
                    WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[routine]%' THEN 'routine'
                    ELSE 'schedule'
                END
            WHERE [type] IS NULL OR LTRIM(RTRIM([type])) = ''
            """
        ))

        db.session.execute(text(
            f"""
            UPDATE {table_ref}
            SET [color] = :default_color
            WHERE [color] IS NULL OR LTRIM(RTRIM([color])) = ''
            """
        ), {'default_color': DEFAULT_SCHEDULE_COLOR})

        if default_user is not None:
            db.session.execute(text(
                f"""
                UPDATE {table_ref}
                SET [user_id] = :user_id
                WHERE [user_id] IS NULL
                """
            ), {'user_id': default_user.id})

        routine_table_ref = None
        routine_columns = set()
        try:
            routine_columns = {column['name'].lower() for column in inspector.get_columns('secretary_routine', schema='dbo')}
            routine_table_ref = 'dbo.secretary_routine'
        except Exception:
            try:
                routine_columns = {column['name'].lower() for column in inspector.get_columns('secretary_routine')}
                routine_table_ref = 'secretary_routine'
            except Exception:
                routine_columns = set()
                routine_table_ref = None

        if routine_table_ref and 'user_id' not in routine_columns:
            db.session.execute(text(f"ALTER TABLE {routine_table_ref} ADD [user_id] INT NULL"))

        if routine_table_ref and default_user is not None:
            db.session.execute(text(
                f"""
                UPDATE {routine_table_ref}
                SET [user_id] = :user_id
                WHERE [user_id] IS NULL
                """
            ), {'user_id': default_user.id})

        db.session.commit()
        _schema_checked = True
    except Exception as exc:
        db.session.rollback()
        app.logger.exception('Schema sync skipped: %s', exc)
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
        ('[routine]', 'routine'),
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
    if upper == 'ROUTINE':
        return 'routine', ''
    if upper == 'PLAN':
        return 'schedule', ''

    return 'schedule', description


def serialize_description(detail: str, schedule_type: str) -> str:
    clean_detail = (detail or '').strip()
    normalized_type = schedule_type if schedule_type in SCHEDULE_TYPES else 'schedule'

    if normalized_type == 'schedule':
        return clean_detail or '계획'
    if normalized_type == 'routine':
        return clean_detail or '루틴'
    return clean_detail


def parse_weekday_values(values) -> list[int]:
    if values is None:
        return []

    source = values
    if isinstance(source, str):
        source = [token.strip() for token in source.split(',') if token.strip()]

    result = []
    if isinstance(source, (list, tuple, set)):
        for token in source:
            try:
                value = int(token)
            except Exception:
                continue
            if 0 <= value <= 6:
                result.append(value)

    return sorted(set(result))


def to_weekdays_text(values: list[int]) -> str:
    return ','.join(str(v) for v in sorted(set(values)))


def normalize_schedule_color(raw_color: str | None) -> str:
    color = (raw_color or '').strip()
    if re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        return color.upper()
    return DEFAULT_SCHEDULE_COLOR


def recover_text(value: str | None) -> str:
    if not isinstance(value, str) or not value:
        return value or ''

    candidates = [value]

    try:
        candidates.append(value.encode('latin1').decode('utf-8'))
    except Exception:
        pass

    try:
        candidates.append(value.encode('latin1').decode('cp949'))
    except Exception:
        pass

    try:
        candidates.append(value.encode('latin1').decode('euc-kr'))
    except Exception:
        pass

    try:
        candidates.append(value.encode('cp1252').decode('utf-8'))
    except Exception:
        pass

    try:
        candidates.append(value.encode('cp1252').decode('cp949'))
    except Exception:
        pass

    try:
        candidates.append(value.encode('cp1252').decode('euc-kr'))
    except Exception:
        pass

    def score(text: str) -> int:
        hangul_count = sum(1 for ch in text if '가' <= ch <= '힣')
        mojibake_count = sum(1 for ch in text if ch in 'ÃÂÐÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜÝÞß')
        broken_kr_count = sum(1 for ch in text if ch in '¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞ')
        replacement_count = text.count('�')
        return hangul_count * 4 - mojibake_count * 2 - broken_kr_count - replacement_count * 3

    best = max(candidates, key=score)
    return best if score(best) > score(value) else value


def schedule_to_payload(schedule: Schedule) -> dict:
    payload = schedule.to_dict()
    recovered_title = recover_text(schedule.title)
    recovered_description = recover_text(schedule.description)
    schedule_type, clean_description = normalize_schedule_data(recovered_description, schedule.schedule_type)
    payload['title'] = recovered_title
    payload['schedule_type'] = schedule_type
    payload['description'] = recover_text(clean_description)
    return payload


def color_preset_to_payload(item: ColorPreset) -> dict:
    payload = item.to_dict()
    payload['name'] = recover_text(payload.get('name', ''))
    return payload


@app.before_request
def ensure_schema_before_request():
    try:
        ensure_schedule_schema()
    except Exception as exc:
        app.logger.exception('Schema pre-check failed but request continues: %s', exc)


@app.before_request
def require_auth_before_request():
    endpoint = request.endpoint or ''
    if endpoint in PUBLIC_ENDPOINTS:
        return None

    if current_user_id() is not None:
        return None

    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    return redirect(url_for('login_page', next=request.path))


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    next_url = request.args.get('next') or request.form.get('next') or '/desktop'
    error = ''

    if request.method == 'POST':
        mode = (request.form.get('mode') or 'login').strip()
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if not username or not password:
            error = '아이디와 비밀번호를 입력하세요.'
        elif mode == 'register':
            exists = User.query.filter(User.username == username).first()
            if exists:
                error = '이미 존재하는 아이디입니다.'
            else:
                try:
                    user = User(username=username, password_hash=generate_password_hash(password))
                    db.session.add(user)
                    db.session.commit()
                    try:
                        ensure_user_color_presets(user.id)
                    except Exception:
                        db.session.rollback()
                    session['user_id'] = user.id
                    session['username'] = user.username
                    return redirect(next_url)
                except Exception:
                    db.session.rollback()
                    error = '회원가입 중 오류가 발생했습니다.'
        else:
            user = User.query.filter(User.username == username).first()
            if not user or not check_password_hash(user.password_hash, password):
                error = '로그인 정보가 올바르지 않습니다.'
            else:
                try:
                    ensure_user_color_presets(user.id)
                except Exception:
                    db.session.rollback()
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect(next_url)

    return render_template('login.html', next_url=next_url, error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/')
def index():
    """홈 페이지 - 데스크톱 이동"""
    if current_user_id() is None:
        return redirect(url_for('login_page'))
    return redirect(url_for('desktop_index'))

# ======================= DESKTOP 라우트 =======================

@app.route('/desktop')
def desktop_index():
    """데스크톱: 일정 목록 (캘린더 뷰)"""
    return render_template('desktop/index.html')

@app.route('/desktop/schedule')
def desktop_get_schedules():
    """데스크톱: 모든 일정 조회 (JSON)"""
    user_id = current_user_id()
    schedules = (
        Schedule.query
        .filter(Schedule.user_id == user_id)
        .order_by(Schedule.start_date.asc())
        .all()
    )
    return jsonify([schedule_to_payload(s) for s in schedules])

@app.route('/desktop/schedule/<int:schedule_id>')
def desktop_get_schedule(schedule_id):
    """데스크톱: 특정 일정 조회"""
    schedule = get_my_schedule_or_404(schedule_id)
    return jsonify(schedule_to_payload(schedule))

@app.route('/desktop/create')
def desktop_create_page():
    """데스크톱: 일정 생성 페이지"""
    return render_template('desktop/create.html')

@app.route('/desktop/weekly')
def desktop_weekly_page():
    """데스크톱: 주간 계획표 페이지"""
    return render_template('desktop/weekly.html')


@app.route('/desktop/manage')
def desktop_manage_page():
    """데스크톱: 일정 일괄 수정 페이지"""
    return render_template('desktop/manage.html')


@app.route('/desktop/color-presets')
def desktop_color_preset_page():
    """데스크톱: 색상 프리셋 관리 페이지"""
    return render_template('desktop/color_presets.html')


@app.route('/desktop/routine-check')
def desktop_routine_check_page():
    """데스크톱: my routine 페이지"""
    return render_template('desktop/routine_check.html')


@app.route('/kids/schedule/list')
def kids_schedule_list():
    """아이들 스케줄 표 이미지 목록"""
    items = []
    try:
        for filename in os.listdir(KIDS_SCHEDULE_FOLDER):
            if not is_allowed_kids_schedule_file(filename):
                continue
            full_path = os.path.join(KIDS_SCHEDULE_FOLDER, filename)
            if not os.path.isfile(full_path):
                continue
            items.append({
                'name': filename,
                'url': url_for('static', filename=f'kids_schedule/{filename}')
            })
    except Exception:
        items = []

    items.sort(key=lambda item: item['name'], reverse=True)
    return jsonify({'files': items})


@app.route('/kids/schedule/upload', methods=['POST'])
def kids_schedule_upload():
    """아이들 스케줄 표 이미지 업로드"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '업로드 파일이 없습니다.'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'message': '파일 이름이 없습니다.'}), 400

    original_name = (file.filename or '').strip()
    if not is_allowed_kids_schedule_file(original_name):
        return jsonify({'success': False, 'message': '지원하지 않는 파일 형식입니다.'}), 400

    base_name, original_ext = os.path.splitext(original_name)
    safe_base = secure_filename(base_name)
    if not original_ext:
        return jsonify({'success': False, 'message': '파일 이름이 올바르지 않습니다.'}), 400

    safe_base = safe_base or 'kids_schedule'

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stored_name = f"{safe_base}_{timestamp}{original_ext.lower()}"
    stored_path = os.path.join(KIDS_SCHEDULE_FOLDER, stored_name)

    try:
        file.save(stored_path)
    except Exception:
        return jsonify({'success': False, 'message': '파일 저장에 실패했습니다.'}), 500

    return jsonify({
        'success': True,
        'file': {
            'name': stored_name,
            'url': url_for('static', filename=f'kids_schedule/{stored_name}')
        }
    })


@app.route('/kids/schedule/delete', methods=['POST'])
def kids_schedule_delete():
    """아이들 스케줄 표 이미지 삭제"""
    data = request.get_json() or {}
    filename = (data.get('filename') or '').strip()
    safe_name = secure_filename(filename)

    if not safe_name or safe_name != filename:
        return jsonify({'success': False, 'message': '파일 이름이 올바르지 않습니다.'}), 400

    if not is_allowed_kids_schedule_file(safe_name):
        return jsonify({'success': False, 'message': '지원하지 않는 파일 형식입니다.'}), 400

    base_folder = os.path.abspath(KIDS_SCHEDULE_FOLDER)
    target_path = os.path.abspath(os.path.join(KIDS_SCHEDULE_FOLDER, safe_name))
    if not (target_path == base_folder or target_path.startswith(base_folder + os.sep)):
        return jsonify({'success': False, 'message': '잘못된 삭제 요청입니다.'}), 400

    if not os.path.isfile(target_path):
        return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'}), 404

    try:
        os.remove(target_path)
    except Exception:
        return jsonify({'success': False, 'message': '파일 삭제에 실패했습니다.'}), 500

    return jsonify({'success': True, 'message': '파일이 삭제되었습니다.'})

@app.route('/desktop/edit/<int:schedule_id>')
def desktop_edit_page(schedule_id):
    """데스크톱: 일정 수정 페이지"""
    schedule = get_my_schedule_or_404(schedule_id)
    return render_template('desktop/edit.html', schedule=schedule)

# ======================= MOBILE 라우트 =======================

@app.route('/mobile')
def mobile_index():
    """모바일: 일정 목록 (리스트 뷰)"""
    return render_template('mobile/index.html')

@app.route('/mobile/schedule')
def mobile_get_schedules():
    """모바일: 모든 일정 조회 (JSON)"""
    user_id = current_user_id()
    schedules = (
        Schedule.query
        .filter(Schedule.user_id == user_id)
        .order_by(Schedule.start_date.asc())
        .all()
    )
    return jsonify([schedule_to_payload(s) for s in schedules])

@app.route('/mobile/schedule/<int:schedule_id>')
def mobile_get_schedule(schedule_id):
    """모바일: 특정 일정 조회"""
    schedule = get_my_schedule_or_404(schedule_id)
    return jsonify(schedule_to_payload(schedule))

@app.route('/mobile/create')
def mobile_create_page():
    """모바일: 일정 생성 페이지"""
    return render_template('mobile/create.html')

@app.route('/mobile/weekly')
def mobile_weekly_page():
    """모바일: 주간 계획표 페이지"""
    return render_template('mobile/weekly.html')

@app.route('/mobile/edit/<int:schedule_id>')
def mobile_edit_page(schedule_id):
    """모바일: 일정 수정 페이지"""
    schedule = get_my_schedule_or_404(schedule_id)
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
    user_id = current_user_id()
    
    try:
        start_date = datetime.fromisoformat(data['start_date'])
        end_date = datetime.fromisoformat(data['end_date']) if data.get('end_date') else None
        
        schedule_type, clean_description = normalize_schedule_data(
            recover_text(data.get('description', '')),
            data.get('schedule_type')
        )

        input_title = recover_text(data.get('title', '')).strip()

        schedule = Schedule(
            title=input_title,
            schedule_type=schedule_type,
            description=serialize_description(clean_description, schedule_type),
            color=normalize_schedule_color(data.get('color')),
            user_id=user_id,
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
    schedule = get_my_schedule_or_404(schedule_id)
    data = request.get_json() or {}
    
    try:
        if 'title' in data:
            schedule.title = recover_text(data.get('title', schedule.title))

        current_type, current_description = normalize_schedule_data(schedule.description, schedule.schedule_type)
        if 'description' in data or 'schedule_type' in data:
            input_description = recover_text(data.get('description', current_description))
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
    schedule = get_my_schedule_or_404(schedule_id)
    
    try:
        db.session.delete(schedule)
        db.session.commit()
        return jsonify({'success': True, 'message': '일정이 삭제되었습니다.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/color-presets', methods=['GET'])
def get_color_presets():
    user_id = current_user_id()

    try:
        ensure_user_color_presets(user_id)
    except Exception:
        db.session.rollback()

    presets = (
        ColorPreset.query
        .filter(ColorPreset.user_id == user_id)
        .order_by(ColorPreset.sort_order.asc(), ColorPreset.id.asc())
        .all()
    )

    changed = False
    for item in presets:
        repaired = recover_text(item.name)
        if repaired and repaired != item.name:
            item.name = repaired
            changed = True

    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    return jsonify({
        'success': True,
        'items': [color_preset_to_payload(item) for item in presets]
    })


@app.route('/api/color-presets', methods=['POST'])
def create_color_preset():
    user_id = current_user_id()
    data = request.get_json() or {}

    name = recover_text(data.get('name', '')).strip()
    color = normalize_schedule_color(data.get('color'))
    sort_order = data.get('sort_order', 0)

    try:
        sort_order = int(sort_order)
    except Exception:
        sort_order = 0

    if not name:
        return jsonify({'success': False, 'message': '프리셋 이름을 입력해 주세요.'}), 400

    try:
        item = ColorPreset(
            user_id=user_id,
            name=name,
            color=color,
            sort_order=sort_order,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'item': color_preset_to_payload(item)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/color-presets/<int:preset_id>', methods=['PUT'])
def update_color_preset(preset_id):
    item = get_my_color_preset_or_404(preset_id)
    data = request.get_json() or {}

    name = recover_text(data.get('name', item.name)).strip()
    color = normalize_schedule_color(data.get('color', item.color))
    sort_order = data.get('sort_order', item.sort_order)

    try:
        sort_order = int(sort_order)
    except Exception:
        sort_order = int(item.sort_order or 0)

    if not name:
        return jsonify({'success': False, 'message': '프리셋 이름을 입력해 주세요.'}), 400

    try:
        item.name = name
        item.color = color
        item.sort_order = sort_order
        db.session.commit()
        return jsonify({'success': True, 'item': color_preset_to_payload(item)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/color-presets/<int:preset_id>', methods=['DELETE'])
def delete_color_preset(preset_id):
    item = get_my_color_preset_or_404(preset_id)

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True, 'message': '프리셋이 삭제되었습니다.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/routines', methods=['GET'])
def get_routines():
    user_id = current_user_id()
    routines = (
        Routine.query
        .filter(Routine.user_id == user_id)
        .order_by(Routine.id.asc())
        .all()
    )
    items = []
    for item in routines:
        payload = item.to_dict()
        payload['name'] = recover_text(payload.get('name', ''))
        items.append(payload)
    return jsonify({'success': True, 'items': items})


@app.route('/api/routines', methods=['POST'])
def create_routine():
    data = request.get_json() or {}
    user_id = current_user_id()
    name = recover_text(data.get('name', '')).strip()
    weekdays = parse_weekday_values(data.get('weekdays'))
    is_active = bool(data.get('is_active', True))

    if not name:
        return jsonify({'success': False, 'message': '루틴 이름은 필수입니다.'}), 400

    if not weekdays:
        return jsonify({'success': False, 'message': '요일을 하나 이상 선택하세요.'}), 400

    try:
        routine = Routine(
            user_id=user_id,
            name=name,
            weekdays=to_weekdays_text(weekdays),
            is_active=is_active
        )
        db.session.add(routine)
        db.session.commit()
        return jsonify({'success': True, 'item': routine.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/routines/<int:routine_id>', methods=['PUT'])
def update_routine(routine_id):
    routine = get_my_routine_or_404(routine_id)
    data = request.get_json() or {}

    name = recover_text(data.get('name', routine.name)).strip()
    weekdays = parse_weekday_values(data.get('weekdays', routine.weekdays))
    is_active = bool(data.get('is_active', routine.is_active))

    if not name:
        return jsonify({'success': False, 'message': '루틴 이름은 필수입니다.'}), 400

    if not weekdays:
        return jsonify({'success': False, 'message': '요일을 하나 이상 선택하세요.'}), 400

    try:
        routine.name = name
        routine.weekdays = to_weekdays_text(weekdays)
        routine.is_active = is_active
        db.session.commit()
        return jsonify({'success': True, 'item': routine.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/routines/<int:routine_id>', methods=['DELETE'])
def delete_routine(routine_id):
    routine = get_my_routine_or_404(routine_id)
    try:
        db.session.delete(routine)
        db.session.commit()
        return jsonify({'success': True, 'message': '루틴이 삭제되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/routine-check')
def get_routine_check_data():
    start_param = (request.args.get('start') or '').strip()
    today = datetime.now().date()

    try:
        if start_param:
            start_date = datetime.fromisoformat(start_param).date()
        else:
            start_date = today
    except ValueError:
        return jsonify({'success': False, 'message': 'start 형식은 YYYY-MM-DD 입니다.'}), 400

    week_start = start_date - timedelta(days=start_date.weekday())
    week_end = week_start + timedelta(days=6)
    week_start_dt = datetime.combine(week_start, time.min)
    week_end_dt = datetime.combine(week_end, time.max)

    user_id = current_user_id()
    routines = (
        Routine.query
        .filter(Routine.user_id == user_id)
        .order_by(Routine.id.asc())
        .all()
    )
    schedule_rows = (
        Schedule.query
        .filter(Schedule.user_id == user_id)
        .filter(Schedule.schedule_type == 'routine')
        .filter(Schedule.start_date >= week_start_dt)
        .filter(Schedule.start_date <= week_end_dt)
        .all()
    )

    completed_map = {}
    for row in schedule_rows:
        desc = (row.description or '').strip()
        match = re.search(r'ROUTINE_ID:(\d+)', desc)
        if not match:
            continue

        routine_id = int(match.group(1))
        day_key = row.start_date.strftime('%Y-%m-%d')
        completed_map.setdefault(day_key, {})[str(routine_id)] = bool(row.is_completed)

    return jsonify({
        'success': True,
        'week_start': week_start.strftime('%Y-%m-%d'),
        'week_end': week_end.strftime('%Y-%m-%d'),
        'routines': [
            {
                **item.to_dict(),
                'name': recover_text(item.name)
            }
            for item in routines
        ],
        'completed_map': completed_map,
    })


@app.route('/api/routine-check/toggle', methods=['POST'])
def toggle_routine_check():
    data = request.get_json() or {}
    user_id = current_user_id()
    try:
        routine_id = int(data.get('routine_id'))
    except Exception:
        return jsonify({'success': False, 'message': 'routine_id가 올바르지 않습니다.'}), 400

    date_text = (data.get('date') or '').strip()
    checked = bool(data.get('checked', False))

    if not date_text:
        return jsonify({'success': False, 'message': 'date가 필요합니다.'}), 400

    try:
        target_date = datetime.fromisoformat(date_text).date()
    except ValueError:
        return jsonify({'success': False, 'message': 'date 형식은 YYYY-MM-DD 입니다.'}), 400

    routine = (
        Routine.query
        .filter(Routine.id == routine_id, Routine.user_id == user_id)
        .first()
    )
    if not routine:
        return jsonify({'success': False, 'message': '루틴을 찾을 수 없습니다.'}), 404

    normalized_name = recover_text(routine.name).strip() or routine.name

    day_start = datetime.combine(target_date, time(hour=9, minute=0))
    day_end = datetime.combine(target_date, time.max)
    marker = f'ROUTINE_ID:{routine_id}'

    schedule = (
        Schedule.query
        .filter(Schedule.user_id == user_id)
        .filter(Schedule.schedule_type == 'routine')
        .filter(Schedule.description == marker)
        .filter(Schedule.start_date >= day_start)
        .filter(Schedule.start_date <= day_end)
        .first()
    )

    try:
        if schedule is None:
            schedule = Schedule(
                title=normalized_name,
                schedule_type='routine',
                description=marker,
                color=DEFAULT_SCHEDULE_COLOR,
                user_id=user_id,
                start_date=day_start,
                end_date=None,
                is_completed=checked
            )
            db.session.add(schedule)
        else:
            schedule.title = normalized_name
            schedule.is_completed = checked

        db.session.commit()
        return jsonify({'success': True, 'message': '체크 상태가 저장되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/weekly-plan')
def weekly_plan_api():
    """주간 계획표 데이터 조회"""
    user_id = current_user_id()
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
        .filter(Schedule.user_id == user_id)
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
        item_title = recover_text(item.title)
        item_description = recover_text(item.description)
        schedule_type, _ = normalize_schedule_data(item_description, item.schedule_type)

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
                    'title': item_title,
                    'color': item.color,
                    'is_completed': bool(item.is_completed)
                })
            continue

        if schedule_type == 'todo':
            todo_by_day[day_key].append({
                'id': item.id,
                'time': None,
                'title': item_title,
                'is_completed': bool(item.is_completed)
            })
            continue

        if schedule_type != 'schedule':
            continue

        hour = item.start_date.hour
        minute_text = f"{item.start_date.minute:02d}"

        if hour in grid:
            label = item_title if item.start_date.minute == 0 else f"{hour}:{minute_text} {item_title}"
            if item.start_date.minute == 0:
                grid[hour][day_key].append({
                    'id': item.id,
                    'title': item_title,
                    'label': label,
                    'is_completed': bool(item.is_completed)
                })
            else:
                grid[hour][day_key].append({
                    'id': item.id,
                    'title': item_title,
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
    user_id = current_user_id()
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

    def parse_relative_weekday(text: str) -> date | None:
        week_day_match = re.search(r'(이번주|이번 주|다음주|다음 주|지난주|지난 주)\s*(월|화|수|목|금|토|일)\s*요일?', text)
        if not week_day_match:
            return None

        week_token, day_token = week_day_match.groups()
        today = datetime.now().date()
        base_monday = today - timedelta(days=today.weekday())

        if week_token in ('다음주', '다음 주'):
            base_monday += timedelta(days=7)
        elif week_token in ('지난주', '지난 주'):
            base_monday -= timedelta(days=7)

        weekday_map = {'월': 0, '화': 1, '수': 2, '목': 3, '금': 4, '토': 5, '일': 6}
        return base_monday + timedelta(days=weekday_map[day_token])

    def parse_date_range(text: str) -> tuple[datetime, datetime]:
        today_date = datetime.now().date()
        start_date = None
        end_date = None

        relative_weekday = parse_relative_weekday(text)
        if relative_weekday:
            start_date = relative_weekday
            end_date = relative_weekday

        if start_date is None and ('오늘' in text):
            start_date = today_date
            end_date = today_date
        elif start_date is None and ('내일' in text):
            start_date = today_date + timedelta(days=1)
            end_date = start_date
        elif start_date is None and ('모레' in text):
            start_date = today_date + timedelta(days=2)
            end_date = start_date
        elif start_date is None and ('이번주' in text or '이번 주' in text):
            start_date = today_date - timedelta(days=today_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif start_date is None and ('다음주' in text or '다음 주' in text):
            start_date = today_date - timedelta(days=today_date.weekday()) + timedelta(days=7)
            end_date = start_date + timedelta(days=6)
        elif start_date is None and ('지난주' in text or '지난 주' in text):
            start_date = today_date - timedelta(days=today_date.weekday()) - timedelta(days=7)
            end_date = start_date + timedelta(days=6)
        elif start_date is None and ('이번달' in text or '이번 달' in text):
            start_date = today_date.replace(day=1)
            next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_month - timedelta(days=1)
        elif start_date is None and ('다음달' in text or '다음 달' in text):
            this_month_start = today_date.replace(day=1)
            next_month_start = (this_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            after_next_month_start = (next_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            start_date = next_month_start
            end_date = after_next_month_start - timedelta(days=1)

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
        monthly_match = re.search(r'(매월|매달)\s*(\d{1,2})\s*일(?:마다)?', text)
        relative_weekday = parse_relative_weekday(text)

        if date_match:
            year, month, day = map(int, date_match.groups())
            target_date = datetime(year, month, day).date()
        elif relative_weekday:
            target_date = relative_weekday
        elif monthly_match:
            monthly_day = int(monthly_match.group(2))
            if 1 <= monthly_day <= 31:
                this_year = now.year
                this_month = now.month
                this_month_last_day = calendar.monthrange(this_year, this_month)[1]
                this_month_day = min(monthly_day, this_month_last_day)
                this_month_target = datetime(this_year, this_month, this_month_day).date()

                if this_month_target >= now.date():
                    target_date = this_month_target
                else:
                    next_month = 1 if this_month == 12 else this_month + 1
                    next_year = this_year + 1 if this_month == 12 else this_year
                    next_month_last_day = calendar.monthrange(next_year, next_month)[1]
                    next_month_day = min(monthly_day, next_month_last_day)
                    target_date = datetime(next_year, next_month, next_month_day).date()
        elif '다음달' in text or '다음 달' in text:
            next_month = 1 if now.month == 12 else now.month + 1
            next_year = now.year + 1 if now.month == 12 else now.year
            day_match = re.search(r'(?:다음달|다음 달)\s*(\d{1,2})\s*일', text)
            if day_match:
                requested_day = int(day_match.group(1))
            else:
                requested_day = 1
            last_day = calendar.monthrange(next_year, next_month)[1]
            final_day = min(max(requested_day, 1), last_day)
            target_date = datetime(next_year, next_month, final_day).date()
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
        cleaned = re.sub(r'(매월|매달)\s*\d{1,2}\s*일(?:마다)?', ' ', cleaned)
        cleaned = re.sub(r'(이번주|이번 주|다음주|다음 주|지난주|지난 주)\s*(월|화|수|목|금|토|일)\s*요일?', ' ', cleaned)
        cleaned = re.sub(r'\d{1,2}:\d{2}', ' ', cleaned)
        cleaned = re.sub(r'(오전|오후)\s*\d{1,2}시\s*\d{0,2}분?', ' ', cleaned)
        cleaned = re.sub(r'\d{1,2}시\s*\d{0,2}분?', ' ', cleaned)
        cleaned = re.sub(r'(오늘|내일|모레|저녁|오전|오후|올해|금년|이번달|이번 달|다음달|다음 달|지난달|지난 달)', ' ', cleaned)

        for keyword in (
            '일정', '스케줄', '추가', '등록', '예약', '잡아줘', '잡아',
            '넣어줘', '넣어', '만들어줘', '만들어', '생성', '해줘', '해주세요',
            '투두', 'todo', '할일', '할 일', '리스트', '목록', '타이틀', 'title', '제목'
        ):
            cleaned = cleaned.replace(keyword, ' ')

        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .,!?-')
        return cleaned or '새 일정'

    def normalize_chat_title(raw_title: str) -> str:
        title = (raw_title or '').strip()
        title = re.sub(r'^(에|를|을|은|는|이|가)\s+', '', title)
        title = re.sub(r'\s+', ' ', title).strip()

        if re.fullmatch(r'재고\s*조사', title):
            return '재고조사'

        return title or '새 일정'

    def resolve_chat_schedule_type(text: str) -> str:
        lowered = text.lower()
        if '투두' in text or 'todo' in lowered or '할일' in text or '할 일' in text:
            return 'todo'
        return 'title'

    def extract_yearly_monthly_dates(text: str, hour: int, minute: int) -> list[datetime]:
        monthly_match = re.search(r'(매월|매달)\s*(\d{1,2})\s*일(?:마다)?', text)
        if not monthly_match:
            return []

        day = int(monthly_match.group(2))
        if day < 1 or day > 31:
            return []

        now_dt = datetime.now()
        target_year = now_dt.year
        datetimes = []
        for month in range(1, 13):
            last_day = calendar.monthrange(target_year, month)[1]
            final_day = min(day, last_day)
            candidate = datetime(target_year, month, final_day, hour=hour, minute=minute)
            if candidate >= now_dt:
                datetimes.append(candidate)
        return datetimes

    if is_weekly_template_request(message):
        try:
            week_start = resolve_week_start(message)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            existing_templates = (
                Schedule.query
                .filter(Schedule.user_id == user_id)
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
                    user_id=user_id,
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
            .filter(Schedule.user_id == user_id)
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
            lines.append(f"- {when} {recover_text(schedule.title)}")

        return jsonify({'success': True, 'message': "\n".join(lines)})

    if not is_create_request(message):
        return jsonify({
            'success': True,
            'message': '일정 생성은 "내일 오후 3시 회의 일정 추가"처럼 말해 주세요.'
        })

    try:
        start_date = parse_target_datetime(message)
        title = normalize_chat_title(recover_text(extract_title(message)))
        schedule_type = resolve_chat_schedule_type(message)
        is_monthly_request = bool(re.search(r'(매월|매달)\s*\d{1,2}\s*일(?:마다)?', message))

        yearly_dates = extract_yearly_monthly_dates(message, start_date.hour, start_date.minute)
        if is_monthly_request and not yearly_dates:
            return jsonify({'success': True, 'message': '오늘 이후에 등록할 매월 일정이 없습니다.'})

        if yearly_dates:
            created_count = 0
            skipped_count = 0

            for target_dt in yearly_dates:
                exists = (
                    Schedule.query
                    .filter(Schedule.user_id == user_id)
                    .filter(Schedule.title == title)
                    .filter(Schedule.schedule_type == schedule_type)
                    .filter(Schedule.start_date == target_dt)
                    .first()
                )
                if exists:
                    skipped_count += 1
                    continue

                schedule = Schedule(
                    title=title,
                    schedule_type=schedule_type,
                    description='',
                    user_id=user_id,
                    start_date=target_dt,
                    end_date=None,
                    is_completed=False
                )
                db.session.add(schedule)
                created_count += 1

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'올해 매월 일정으로 {created_count}건 등록했어요 (중복 {skipped_count}건 제외): {title}'
            })

        schedule = Schedule(
            title=title,
            schedule_type=schedule_type,
            description='',
            user_id=user_id,
            start_date=start_date,
            end_date=None,
            is_completed=False
        )

        db.session.add(schedule)
        db.session.commit()

        when = start_date.strftime('%Y-%m-%d %H:%M')
        type_label = '투두' if schedule_type == 'todo' else '제목'
        return jsonify({'success': True, 'message': f'{type_label}로 등록했어요: {when} {title}'})
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
