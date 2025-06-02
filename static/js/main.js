function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

function rebindScrollReveal() {
    const reveals = document.querySelectorAll(".scroll-reveal");
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("opacity-100", "translate-y-0");
                entry.target.classList.remove("opacity-0", "translate-y-6");
            }
        });
    }, { threshold: 0.1 });

    reveals.forEach(el => observer.observe(el));
}

function ajaxifyLinks() {
    document.querySelectorAll('a.ajax-link').forEach(link => {
        const newLink = link.cloneNode(true);
        link.replaceWith(newLink);
        newLink.addEventListener('click', function (e) {
            e.preventDefault();
            const url = this.href;
            const currentPath = window.location.pathname;
            const targetPath = new URL(url, window.location.origin).pathname;

            if (currentPath === targetPath) return;

            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(res => res.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newContent = doc.querySelector('#main-content');
                    if (newContent) {
                        document.getElementById('main-content').innerHTML = newContent.innerHTML;
                        window.history.pushState(null, '', targetPath);
                        ajaxifyLinks();
                        rebindDynamicButtons();
                        rebindScrollReveal();
                        rebindUploadForms();
                    }
                });
        });
    });
}

function rebindDynamicButtons() {
    document.querySelectorAll('form[action*="delete"]').forEach(form => {
        form.addEventListener('submit', function (e) {
            if (!confirm('정말 삭제하시겠습니까?')) {
                e.preventDefault();
            }
        });
    });
}

function previewAndUploadImage() {
    const fileInput = document.getElementById("imageInput");
    const form = document.getElementById("imageForm");

    if (!fileInput || !form || !fileInput.files.length) {
        alert("업로드할 이미지를 선택하세요.");
        return;
    }

    const formData = new FormData(form);
    fetch("/upload_image", {
        method: "POST",
        body: formData,
        headers: {
            "X-Requested-With": "XMLHttpRequest"
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("이미지 업로드 성공!");
            fetch("/gallery", {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
            .then(res => res.text())
            .then(html => {
                document.getElementById("main-content").innerHTML = html;
                ajaxifyLinks();
                rebindDynamicButtons();
                rebindScrollReveal();
                rebindUploadForms();
            });
        } else {
            alert("업로드 실패: " + data.error);
        }
    });
}

function validateVideoFile(file) {
    const maxSize = 100 * 1024 * 1024; // 100MB 제한

    if (file.size > maxSize) {
        alert('파일 크기는 100MB를 초과할 수 없습니다.');
        return false;
    }

    if (!file.type.match('video.*')) {
        alert('비디오 파일만 업로드 가능합니다.');
        return false;
    }
    return true;
}

function previewAndUploadVideo() {
    const fileInput = document.getElementById("video");
    const form = document.getElementById("videoForm");

    if (!fileInput || !form || !fileInput.files.length) {
        alert("업로드할 영상을 선택하세요.");
        return;
    }

    const file = fileInput.files[0];
    if (!validateVideoFile(file)) {
        fileInput.value = '';
        return;
    }

    const formData = new FormData(form);
    fetch("/upload_video", {
        method: "POST",
        body: formData,
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCSRFToken()
        }
    })
    .then(res => {
        if (!res.ok) {
            throw new Error('서버 오류가 발생했습니다.');
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            alert("영상 업로드 성공!");
            fetch("/videos", {
                headers: { 
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": getCSRFToken()
                }
            })
            .then(res => res.text())
            .then(html => {
                document.getElementById("main-content").innerHTML = html;
                ajaxifyLinks();
                rebindDynamicButtons();
                rebindScrollReveal();
                rebindUploadForms();
            })
            .catch(error => {
                console.error('페이지 새로고침 중 오류:', error);
                alert('페이지를 새로고침 해주세요.');
            });
        } else {
            alert("업로드 실패: " + (data.error || "알 수 없는 오류가 발생했습니다."));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.message || "업로드 중 오류가 발생했습니다.");
    });
}

function rebindUploadForms() {
    const imageForm = document.getElementById("imageForm");
    const imageInput = document.getElementById("imageInput");
    if (imageForm && imageInput) {
        imageForm.addEventListener("submit", function (e) {
            if (!imageInput.files.length) {
                e.preventDefault();
                alert("업로드할 이미지를 선택하세요.");
            }
        });
    }

    const videoForm = document.getElementById("videoForm");
    const videoInput = document.getElementById("video");
    if (videoForm && videoInput) {
        videoForm.addEventListener("submit", function (e) {
            if (!videoInput.files.length) {
                e.preventDefault();
                alert("업로드할 영상을 선택하세요.");
            }
        });
    }
}

function deleteImage(imageId, parentElement) {
    if (confirm("정말 삭제하시겠습니까?")) {
        fetch(`/delete_image/${imageId}`, {
            method: "POST",
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && parentElement) parentElement.remove();
            else alert(data.error || "삭제에 실패했습니다.");
        });
    }
}

function deleteVideo(videoId) {
    if (!confirm("정말 삭제하시겠습니까?")) {
        return;
    }

    fetch(`/delete_video/${videoId}`, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(res => {
        if (!res.ok) {
            throw new Error('서버 오류가 발생했습니다.');
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            const videoElement = document.getElementById(`video-${videoId}`);
            if (videoElement) {
                videoElement.remove();
                
                // 비디오가 모두 삭제되었는지 확인
                const gallery = document.getElementById('videoGallery');
                if (gallery && !gallery.children.length) {
                    gallery.innerHTML = '<p class="col-span-full text-center text-gray-500">아직 업로드 된 동영상이 없습니다.</p>';
                }
            }
        } else {
            throw new Error(data.error || "삭제 실패");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.message || "삭제 중 오류가 발생했습니다.");
    });
}

let currentTrack = 0;
const audio = document.getElementById("audioPlayer");
const source = document.getElementById("audioSource");
const btn = document.getElementById("playPauseBtn");
const title = document.getElementById("trackTitle");
const nextBtn = document.getElementById("nextTrackBtn");
const volumeSlider = document.getElementById("volumeSlider");

const filenames = window.filenames || [];
const trackNames = window.trackNames || [];
const basePath = "/static/audio/";
const playlist = filenames.map(name => basePath + name);

function playTrack(index, resumeTime = null) {
    if (!playlist.length) return;
    if (source.src.endsWith(playlist[index]) && !audio.paused) return;

    source.src = playlist[index];
    audio.load();
    audio.addEventListener("loadedmetadata", () => {
        if (resumeTime !== null) {
            audio.currentTime = resumeTime;
        }
        audio.play();
    }, { once: true });

    title.textContent = trackNames[index] || "재생 중";
    btn.textContent = "⏸️";
}

function savePlaybackState() {
    localStorage.setItem("liz_currentTrack", currentTrack);
    localStorage.setItem("liz_currentTime", audio.currentTime);
}

audio.addEventListener("timeupdate", savePlaybackState);
audio.addEventListener("ended", () => {
    currentTrack = (currentTrack + 1) % playlist.length;
    playTrack(currentTrack);
});

btn.addEventListener("click", () => {
    if (audio.paused) {
        audio.play();
        btn.textContent = "⏸️";
    } else {
        audio.pause();
        btn.textContent = "▶️";
    }
});

nextBtn.addEventListener("click", () => {
    currentTrack = (currentTrack + 1) % playlist.length;
    playTrack(currentTrack);
});

volumeSlider.addEventListener("input", () => {
    audio.volume = volumeSlider.value;
});

document.addEventListener("DOMContentLoaded", () => {
    ajaxifyLinks();
    rebindDynamicButtons();
    rebindScrollReveal();
    rebindUploadForms();

    const storedTrack = localStorage.getItem("liz_currentTrack");
    const storedTime = localStorage.getItem("liz_currentTime");

    if (storedTrack !== null) {
        currentTrack = parseInt(storedTrack);
        const resumeTime = storedTime !== null ? parseFloat(storedTime) : null;
        playTrack(currentTrack, resumeTime);
    } else {
        const unlock = ()=> {
            playTrack(currentTrack);
            document.removeEventListener("click", unlock);
        };
        document.addEventListener("click", unlock);
    }
});