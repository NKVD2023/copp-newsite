document.addEventListener("DOMContentLoaded", function() {
    const defaultSettings = {
        active: false,
        theme: 'bw', // bw, wb, blue, brown, green
        fontSize: 1, // 1 (18px), 2 (24px), 3 (30px)
        images: 'on', // on, off, grayscale
        speech: false
    };

    let bviSettings = JSON.parse(localStorage.getItem('bviSettings')) || defaultSettings;
    const body = document.body;
    const html = document.documentElement;
    let synth = window.speechSynthesis;

    function applySettings() {
        if (!bviSettings.active) {
            body.classList.remove('bvi-mode');
            body.className = body.className.replace(/bvi-theme-\w+/g, '');
            body.classList.remove('bvi-img-off', 'bvi-img-grayscale');
            html.className = html.className.replace(/bvi-font-\d/g, '');
            synth.cancel();
            updatePanelActiveButtons();
            return;
        }

        body.classList.add('bvi-mode');
        
        // Очищаем старые классы
        body.className = body.className.replace(/bvi-theme-\w+/g, '');
        body.classList.remove('bvi-img-off', 'bvi-img-grayscale');
        html.className = html.className.replace(/bvi-font-\d/g, '');

        // Применяем новые классы
        body.classList.add('bvi-theme-' + bviSettings.theme);
        html.classList.add('bvi-font-' + bviSettings.fontSize);
        
        if (bviSettings.images === 'off') {
            body.classList.add('bvi-img-off');
        } else if (bviSettings.images === 'grayscale') {
            body.classList.add('bvi-img-grayscale');
        }

        updatePanelActiveButtons();
    }

    function saveSettings() {
        localStorage.setItem('bviSettings', JSON.stringify(bviSettings));
        applySettings();
    }

    function updatePanelActiveButtons() {
        // Подсветка активных кнопок
        document.querySelectorAll('.bvi-btn').forEach(btn => btn.classList.remove('active'));
        
        const btnTheme = document.getElementById('bvi-theme-' + bviSettings.theme);
        if(btnTheme) btnTheme.classList.add('active');

        const btnImg = document.getElementById('bvi-img-' + bviSettings.images);
        if(btnImg) btnImg.classList.add('active');

        const btnSpeech = document.getElementById('bvi-speech-' + (bviSettings.speech ? 'on' : 'off'));
        if(btnSpeech) btnSpeech.classList.add('active');
    }

    // Слушатели событий
    window.bviToggle = function() {
        if(!bviSettings.active) {
            bviSettings.active = true;
            bviSettings.theme = 'bw'; // по умолчанию черно-белая
            bviSettings.fontSize = 2; // увеличенный шрифт
            bviSettings.images = 'grayscale';
        } else {
            bviSettings.active = false;
        }
        saveSettings();
    };

    window.bviSetTheme = function(theme) { bviSettings.theme = theme; saveSettings(); };
    window.bviChangeFont = function(delta) {
        bviSettings.fontSize += delta;
        if (bviSettings.fontSize < 1) bviSettings.fontSize = 1;
        if (bviSettings.fontSize > 3) bviSettings.fontSize = 3;
        saveSettings();
    };
    window.bviSetImages = function(mode) { bviSettings.images = mode; saveSettings(); };
    window.bviSetSpeech = function(active) { bviSettings.speech = active; saveSettings(); };

    // Обработчик синтеза речи (читает выделенный текст)
    document.addEventListener('mouseup', () => {
        if(!bviSettings.active || !bviSettings.speech) return;
        let text = window.getSelection().toString().trim();
        if(text) {
            synth.cancel(); // останавливаем предыдущее чтение
            let msg = new SpeechSynthesisUtterance(text);
            msg.lang = 'ru-RU';
            synth.speak(msg);
        }
    });

    // Звуковое сопровождение при наведении на элементы (если синтез включен)
    let speechTimer = null;
    document.addEventListener('mouseover', (e) => {
        if(!bviSettings.active || !bviSettings.speech) return;
        let target = e.target.closest('a, button, h1, h2, h3, h4, h5, h6, label, p, span, .bvi-btn');
        if(!target) return;
        
        let text = target.getAttribute('aria-label') || target.title || target.innerText;
        if(text && text.trim()) {
            clearTimeout(speechTimer);
            speechTimer = setTimeout(() => {
                synth.cancel();
                let msg = new SpeechSynthesisUtterance(text.trim());
                msg.lang = 'ru-RU';
                synth.speak(msg);
            }, 600); // Задержка перед чтением при наведении
        }
    });

    document.addEventListener('mouseout', (e) => {
        clearTimeout(speechTimer);
    });

    applySettings();
});
