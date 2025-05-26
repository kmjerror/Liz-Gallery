import os
from datetime import datetime
from app import app, db, Song

AUDIO_FOLDER = os.path.join(app.static_folder, 'audio')

with app.app_context():
    for filename in os.listdir(AUDIO_FOLDER):
        if filename.endswith(".mp3"):
            title = filename.rsplit('.', 1)[0].replace('_',' ')
            existing = Song.query.filter_by(filename=filename).first()
            if not existing:
                song = Song(title=title, filename=filename, uploaded_at=datetime.now())
                db.session.add(song)
    db.session.commit()
    print("🎵 오디오 파일 기반 DB 복원 완료.")