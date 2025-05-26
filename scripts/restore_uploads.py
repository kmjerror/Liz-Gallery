import os
from datetime import datetime
from app import db, Image, Video, User, app

with app.app_context():
    admin = User.query.filter_by(username='LizHolic').first()
    if not admin:
        print("❗ 관리자 계정이 존재하지 않습니다. 먼저 생성해 주세요.")
        exit()

    # 이미지 등록
    image_folder = os.path.join(app.static_folder, 'uploads', 'images')
    image_files = os.listdir(image_folder)
    restored_images = 0

    for fname in image_files:
        # 이미 DB에 있는지 확인
        if not Image.query.filter_by(filename=fname).first():
            new_image = Image(filename=fname, uploader_id=admin.id, uploaded_at=datetime.now())
            db.session.add(new_image)
            restored_images += 1

    # 동영상 등록
    video_folder = os.path.join(app.static_folder, 'uploads', 'videos')
    video_files = os.listdir(video_folder)
    restored_videos = 0

    for fname in video_files:
        if not Video.query.filter_by(filename=fname).first():
            new_video = Video(filename=fname, uploader_id=admin.id, uploaded_at=datetime.now())
            db.session.add(new_video)
            restored_videos += 1

    db.session.commit()
    print(f"✅ 이미지 {restored_images}개, 동영상 {restored_videos}개를 복구했습니다.")
