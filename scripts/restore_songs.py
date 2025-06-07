import sys
import os
from datetime import datetime


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Song  

AUDIO_FOLDER = os.path.join(app.static_folder, 'audio')

with app.app_context():
    restored_count = 0

    for filename in os.listdir(AUDIO_FOLDER):
        if filename.endswith(".mp3"):
            raw_title = filename.rsplit('.', 1)[0]
            parts = raw_title.split('_')

            if len(parts) >= 2 and parts[0][:4].isdigit():
                title = ' '.join(parts[1:])
            else:
                title = ' '.join(parts)

            existing = Song.query.filter_by(filename=filename).first()
            if not existing:
                song = Song(title=title, filename=filename, uploaded_at=datetime.now())
                db.session.add(song)
                restored_count += 1

    db.session.commit()
    print(f"🎵 오디오 파일 기반 DB 복원 완료: {restored_count}곡 추가됨.")