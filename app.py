import os
import re
import subprocess
import sqlite3
from itsdangerous import URLSafeTimeSerializer, SignatureExpired, BadSignature
from flask_mail import Mail, Message
from flask_wtf import CSRFProtect
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash


KST = timezone(timedelta(hours=9))


app = Flask(__name__)
app.secret_key = 'rhkralswns12?'
s = URLSafeTimeSerializer(app.config['SECRET_KEY'])
csrf = CSRFProtect(app)
csrf.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fanpage.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


def is_admin():
    return current_user.is_authenticated and current_user.is_admin


db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(KST))

    def __repr__(self):
        return f'<Schedule {self.title}>'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_notice = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(KST))


    author = db.relationship('User', backref=db.backref('posts', lazy=True))


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER_IMAGES'] = os.path.join(BASE_DIR, 'static', 'uploads', 'images')
app.config['UPLOAD_FOLDER_VIDEOS'] = os.path.join(BASE_DIR, 'static', 'uploads', 'videos')
app.config['UPLOAD_FOLDER_AUDIO'] = os.path.join(BASE_DIR, 'static', 'audio')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '6945830a@gmail.com'
app.config['MAIL_PASSWORD'] = 'wuba wwsx kqhk jeal'
app.config['MAIL_DEFAULT_SENDER'] = '6945830a@gmail.com'

mail = Mail(app)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'wmv', 'mkv'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(KST))
    description = db.Column(db.String(10), nullable=True)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(KST))
    description = db.Column(db.String(10), nullable=True)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(KST))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    author = db.relationship('User', backref='comments')
    post = db.relationship('Post', backref='comments')


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(KST))


@app.context_processor
def inject_songs():
    songs = Song.query.order_by(Song.uploaded_at.asc()).all()
    return dict(songs=songs)


@app.route('/admin')
@login_required
def admin_page():
    print("🔍 current_user:", current_user)
    print("🔍 is_authenticated:", current_user.is_authenticated)
    print("🔍 is_admin:", current_user.is_admin)

    if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
        flash("관리자만 접근할 수 있습니다.")
        return redirect(url_for('dashboard'))
    
    image_folder = os.path.join(app.static_folder, 'uploads/images')
    video_folder = os.path.join(app.static_folder, 'uploads/videos')

    image_files = []
    if os.path.exists(image_folder):
        image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    video_files = []
    if os.path.exists(video_folder):
        video_files = [f for f in os.listdir(video_folder) if f.lower().endswith(('.mp4', '.webm' '.mov'))]

    posts = Post.query.order_by(Post.created_at.desc()).all()

    if  request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("admin/admin_content.html", image_files=image_files, video_files=video_files, posts=posts)

    return render_template(
        'admin/admin.html',
        image_files=image_files,
        video_files=video_files,
        posts=posts
    )


@app.route('/admin/users')
@login_required
def user_list():
    if not current_user.is_admin:
        flash("접근 권한이 없습니다.")
        return redirect(url_for('home'))
    
    users = User.query.all()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("admin/admin_users_content.html", users=users)
    return render_template('admin/admin_users.html', users=users)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("권한이 없습니다.")
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("관리자 계정은 삭제할 수 없습니다.")
        return redirect(url_for('user_list'))
    
    db.session.delete(user)
    db.session.commit()
    flash("사용자 삭제 완료.")
    return redirect(url_for('user_list'))


@app.route('/admin/schedules', methods=['GET', 'POST'])
@login_required
def manage_schedules():
    if not current_user.is_admin:
        flash("접근 권한이 없습니다.")
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        title = request.form['title']
        date_str = request.form['date']
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        location = request.form.get('location')
        note = request.form.get('note')

        new_schedule = Schedule(title=title, date=date, location=location, note=note)
        db.session.add(new_schedule)
        db.session.commit()
        flash('일정이 등록되었습니다.')
        return redirect(url_for('manage_schedules'))
    
    schedules = Schedule.query.order_by(Schedule.date.asc()).all()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("admin/admin_schedules_content.html", schedules=schedules)
    return render_template('admin/admin_schedules.html', schedules=schedules)


@app.route('/admin/schedules/delete/<int:schedule_id>', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    if not current_user.is_admin:
        flash("접근 권한이 없습니다.")
        return redirect(url_for('home'))
    
    schedule = Schedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()
    flash("일정이 삭제되었습니다.")
    return redirect(url_for('manage_schedules'))


@app.route('/admin/songs', methods=['GET', 'POST'])
@login_required
def manage_songs():
    if not is_admin():
        flash("접근 권한이 없습니다.")
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        file = request.files.get('song')
        title = request.form.get('title', '').strip()

        if file and file.filename.endswith('.mp3') and title:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            audio_path = os.path.join(app.config['UPLOAD_FOLDER_AUDIO'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER_AUDIO'], exist_ok=True)
            file.save(audio_path)

            new_song = Song(title=title, filename=filename)
            db.session.add(new_song)
            db.session.commit()

            flash("곡이 업로드되었습니다.")
            return redirect(url_for('manage_songs'))
        else:
            flash("mp3 파일과 제목을 정확히 입력해주세요.")

    songs = Song.query.order_by(Song.uploaded_at.desc()).all()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("admin/admin_songs_content.html", songs=songs)
    return render_template("admin/admin_songs.html", songs=songs)


@app.route('/')
def home():
    posts = Post.query.filter_by(is_notice=True).order_by(Post.created_at.desc()).limit(3).all()
    schedules = Schedule.query.order_by(Schedule.date.asc()).limit(5).all()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("home/home_content.html", posts=posts, schedules=schedules)
    return render_template('home/home.html', user=current_user, posts=posts, schedules=schedules)


@app.route('/register', methods=['GET', 'POST'])
def register():
    songs = Song.query.all()
    
    if request.method == 'POST':
        username = request.form['username']
        password_plain = request.form['password']
        email = request.form['email']

        if User.query.filter_by(email=email).first():
            flash('이미 존재하는 이메일일입니다.')
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return render_template("auth/register_content.html")
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('이미 사용 중인 아이디입니다.')
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return render_template("auth/register_content.html")
            return redirect(url_for('register'))
        
        password_pattern = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$'
        if not re.match(password_pattern, password_plain):
            flash('비밀번호는 8자 이상이며 영문자, 숫자, 특수문자를 포함해야 합니다.')
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return render_template("auth/register_content.html")
            return redirect(url_for('register'))
                

        hashed_password = generate_password_hash(password_plain)
        new_user = User(username=username, password=hashed_password, email=email, is_verified=False)
        db.session.add(new_user)
        db.session.commit()
        
        token = s.dumps(email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)

        msg = Message('LIZ공식갤러리 이메일 인증', sender='6945830a@gmail.com', recipients=[email])
        msg.body = f'{username}님, 아래 링크를 클릭하여 이메일 인증을 완료해주세요:\n\n{confirm_url}'
        mail.send(msg)

        flash('인증 메일을 보냈습니다. 메일함을 확인해주세요.')
        return redirect(url_for('login'))
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render_template("auth/register_content.html", songs=songs)
    return render_template('auth/register.html', songs=songs)


@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        return '인증 링크가 만료되었습니다.'
    except BadSignature:
        return '잘못된 인증 링크입니다.'
    
    user = User.query.filter_by(email=email).first_or_404()
    if user.is_verified:
        return '이미 이메일 인증이 완료된 계정입니다.'
    
    user.is_verified = True
    db.session.commit()
    return '이메일 인증이 완료되었습니다. 이제 로그인할 수 있습니다.'


@app.route('/check_username')
def check_username():
    username = request.args.get('username', '')
    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({'exists': exists})


@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    file = request.files.get('image')
    if file and allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        if not file.mimetype.startswith("image/"):
            error_msg = "잘못된 이미지 형식입니다."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(success=False, error=error_msg)
            flash(error_msg)
            return redirect(url_for('gallery'))

        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER_IMAGES'], exist_ok=True)
        file.save(filepath)

        description = request.form.get('description', '')[:10]
        new_image = Image(filename=filename, uploader_id=current_user.id, description=description)
        db.session.add(new_image)
        db.session.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            image_url = url_for('static', filename='uploads/images/' + filename)
            return jsonify(success=True, image_url=image_url, image_id=new_image.id)

        # 일반 폼 제출이라면
        flash("이미지가 업로드되었습니다.")
        return redirect(url_for('gallery'))

    error_msg = "허용되지 않는 파일 형식입니다."
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(success=False, error=error_msg)
    flash(error_msg)
    return redirect(url_for('gallery'))


@app.route('/delete_image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    image = Image.query.get_or_404(image_id)
    if image.uploader_id != current_user.id and not current_user.is_admin:
        return jsonify(success=False, error="권한이 없습니다.")
    
    image_path = os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], image.filename)
    if os.path.exists(image_path):
        os.remove(image_path)


    db.session.delete(image)
    db.session.commit()
    return jsonify(success=True)


def reencode_video(input_path, output_path):

    try:
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-profile:v", "main",
            "-level", "3.1",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        return False


@app.route('/upload_video', methods=['POST'])
@login_required
def upload_video():
    file = request.files.get('video')
    description = request.form.get('description', '')[:10]

    if file and allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        if not file.mimetype.startswith("video/"):
            return jsonify(success=False, error="잘못된 동영상 형식입니다.")
        
        origianl_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        base_filename = f"{timestamp}_{origianl_filename.rsplit('.', 1)[0]}"
        
        folder = app.config['UPLOAD_FOLDER_VIDEOS']
        os.makedirs(folder, exist_ok=True)


        original_ext = origianl_filename.rsplit('.', 1)[1].lower()
        original_path = os.path.join(folder, f"{base_filename}_orig.{original_ext}")
        file.save(original_path)


        converted_filename = f"{base_filename}.mp4"
        converted_path = os.path.join(folder, converted_filename)


        success = reencode_video(original_path, converted_path)
        if not success:

            if os.path.exists(original_path):
                os.remove(original_path)
            return jsonify(success=False, error="동영상 인코딩 실패")
        

        if os.path.exists(original_path):
            os.remove(original_path)


        new_video = Video(filename=converted_filename, uploader_id=current_user.id)
        db.session.add(new_video)
        db.session.commit()


        video_url = url_for('static', filename='uploads/videos/' + converted_filename)
        return jsonify(success=True, video_url=video_url, video_id=new_video.id)
    return jsonify(success=False, error="업로드 실패 또는 파일 형식 오류")


@app.route('/delete_video/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    if video.uploader_id != current_user.id and not current_user.is_admin:
        return jsonify(success=False, error="권한이 없습니다.")
    

    video_path = os.path.join(app.config['UPLOAD_FOLDER_VIDEOS'], video.filename)
    if os.path.exists(video_path):
        os.remove(video_path)


    db.session.delete(video)
    db.session.commit()
    return jsonify(success=True)


@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user and not current_user.is_admin:
        flash('글을 삭제할 권한이 없습니다.')
        return redirect(url_for('home'))
    
    db.session.delete(post)
    db.session.commit()
    flash('글이 삭제되었습니다.')
    return redirect(url_for('home'))


@app.route('/write_post', methods=['GET', 'POST'])
@login_required
def write_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        new_post = Post(title=title, content=content, author_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()

        flash('글이 성공적으로 등록되었습니다.')
        return redirect(url_for('board'))
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template('board/write_post_content.html', user=current_user)
    return render_template('board/write_post.html', user=current_user)


@app.route('/write_notice', methods=['GET', 'POST'])
@login_required
def write_notice():
    if not current_user.is_admin:
        flash("관리자만 공지를 작성할 수 있습니다.")
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        notice = Post(title=title, content=content, is_notice=True, author_id=current_user.id)
        db.session.add(notice)
        db.session.commit()

        flash('공지사항이 등록되었습니다.')
        return redirect(url_for('home'))
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template('board/write_notice_content.html')
    return render_template('board/write_notice.html')


@app.route('/board')
@login_required
def board():
    posts = Post.query.filter_by(is_notice=False).order_by(Post.created_at.desc()).all()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("board/board_content.html", posts=posts)
    return render_template('board/board.html', posts=posts)


@app.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form['content']
    new_comment = Comment(content=content, author_id=current_user.id, post_id=post_id)
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author_id != current_user.id and not current_user.is_admin:
        flash("삭제 권한이 없습니다.")
        return redirect(url_for('home'))
    

    db.session.delete(comment)
    db.session.commit()
    flash("댓글이 삭제되었습니다.")
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("dashboard/dashboard_content.html", user=current_user)
    return render_template('dashboard/dashboard.html', user=current_user)


@app.route('/gallery', methods=['GET', 'POST'])
@login_required
def gallery():
    images = Image.query.order_by(Image.uploaded_at.desc()).all()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("media/gallery_content.html", images=images)
    return render_template("media/gallery.html", images=images)


@app.route('/videos', methods=['GET', 'POST'])
@login_required
def videos():
    videos = Video.query.order_by(Video.uploaded_at.desc()).all()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("media/videos_content.html", videos=videos)
    return render_template('media/videos.html', videos=videos)


@app.route('/login', methods=['GET', 'POST'])
def login():
    songs = Song.query.all()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.')

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render_template("auth/login_content.html", songs=songs)
        return render_template('auth/login.html', songs=songs)
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("auth/login_content.html", songs=songs)
    return render_template('auth/login.html', songs=songs)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()


        admin = User.query.filter_by(username='LizHolic').first()
        if admin:
            admin.is_admin = True
            db.session.commit()
            print("LizHolic 계정에 관리자 권한이 부여되었습니다.")
        else:
            print("LizHolic 계정을 찾을 수 없습니다.")