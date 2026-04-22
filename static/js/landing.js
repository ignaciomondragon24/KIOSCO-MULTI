/*
 * Landing Kiosco Pro — player hero + lightbox de capturas.
 *
 * El "video demo" del hero es en realidad un carrusel que auto-rota entre
 * las 6 capturas reales del sistema. Es mas rapido de mantener que un video
 * grabado (no se desactualiza cuando cambia la UI).
 */
(function () {
    'use strict';

    // =====================================================================
    // 1. Hero player (carrusel autoplay)
    // =====================================================================
    function initHeroPlayer() {
        var player = document.getElementById('hero-player');
        if (!player) return;

        var slides = player.querySelectorAll('.hero__player-slide');
        var dots = player.querySelectorAll('.hero__player-dots button');
        var caption = player.querySelector('.hero__player-caption');
        var progress = player.querySelector('.hero__player-progress span');
        var toggle = player.querySelector('.hero__player-toggle');

        if (!slides.length) return;

        var current = 0;
        var playing = true;
        var interval = null;
        var SLIDE_MS = 3500;

        function show(index) {
            current = (index + slides.length) % slides.length;
            slides.forEach(function (s, i) {
                s.classList.toggle('is-active', i === current);
            });
            dots.forEach(function (d, i) {
                d.classList.toggle('is-active', i === current);
            });
            if (caption) {
                caption.innerHTML = slides[current].dataset.caption || '';
            }
            restartProgress();
        }

        function restartProgress() {
            if (!progress) return;
            progress.style.transition = 'none';
            progress.style.width = '0%';
            // Forzar reflow para que el navegador aplique width:0 antes de la transicion
            void progress.offsetWidth;
            if (playing) {
                progress.style.transition = 'width ' + SLIDE_MS + 'ms linear';
                progress.style.width = '100%';
            }
        }

        function next() { show(current + 1); }

        function start() {
            stop();
            interval = setInterval(next, SLIDE_MS);
            playing = true;
            if (toggle) {
                toggle.innerHTML = '<i class="fas fa-pause"></i>';
                toggle.dataset.state = 'playing';
            }
            restartProgress();
        }

        function stop() {
            if (interval) clearInterval(interval);
            interval = null;
            playing = false;
            if (toggle) {
                toggle.innerHTML = '<i class="fas fa-play"></i>';
                toggle.dataset.state = 'paused';
            }
            if (progress) {
                // Congelar la barra donde este
                var computed = window.getComputedStyle(progress).width;
                progress.style.transition = 'none';
                progress.style.width = computed;
            }
        }

        if (toggle) {
            toggle.addEventListener('click', function () {
                if (playing) stop(); else start();
            });
        }

        dots.forEach(function (dot) {
            dot.addEventListener('click', function () {
                var idx = parseInt(dot.dataset.slide, 10);
                show(idx);
                if (playing) start();
            });
        });

        // Pausar cuando no esta visible para ahorrar pintado
        if ('IntersectionObserver' in window) {
            var io = new IntersectionObserver(function (entries) {
                entries.forEach(function (e) {
                    if (e.isIntersecting) {
                        if (!playing) start();
                    } else {
                        if (playing) stop();
                    }
                });
            }, { threshold: 0.2 });
            io.observe(player);
        }

        show(0);
        start();
    }

    // =====================================================================
    // 2. Lightbox para capturas del sistema
    // =====================================================================
    function initLightbox() {
        var lightbox = document.getElementById('lightbox');
        if (!lightbox) return;

        var cards = document.querySelectorAll('[data-lightbox]');
        if (!cards.length) return;

        var img = document.getElementById('lightbox-img');
        var caption = document.getElementById('lightbox-caption');
        var btnClose = lightbox.querySelector('.lightbox__close');
        var btnPrev = lightbox.querySelector('.lightbox__nav--prev');
        var btnNext = lightbox.querySelector('.lightbox__nav--next');
        var heroPlayer = document.getElementById('hero-player');

        // Construir la galeria desde las cards
        var gallery = Array.prototype.map.call(cards, function (card) {
            var imgEl = card.querySelector('img');
            return {
                src: imgEl ? imgEl.src : '',
                alt: imgEl ? imgEl.alt : '',
                caption: card.dataset.caption || (imgEl ? imgEl.alt : ''),
            };
        });

        // Si el hero player existe, permitir ampliar el slide activo
        function openHeroActive() {
            if (!heroPlayer) return;
            var active = heroPlayer.querySelector('.hero__player-slide.is-active');
            if (!active) return;
            var activeSrc = active.getAttribute('src');
            // Buscar la card de capturas que coincide por filename para reutilizar su posicion
            var idx = -1;
            for (var i = 0; i < gallery.length; i++) {
                if (gallery[i].src.indexOf(basename(activeSrc)) !== -1) { idx = i; break; }
            }
            if (idx === -1) {
                // Fallback: abrir solo esa imagen sin nav
                currentIdx = 0;
                img.src = active.src;
                img.alt = active.alt;
                caption.innerHTML = active.dataset.caption || active.alt || '';
                lightbox.hidden = false;
                lightbox.setAttribute('aria-hidden', 'false');
                document.body.classList.add('lightbox-open');
                requestAnimationFrame(function () { lightbox.classList.add('is-visible'); });
                return;
            }
            open(idx);
        }

        function basename(path) {
            if (!path) return '';
            return path.split('/').pop().split('?')[0];
        }

        var currentIdx = 0;

        function open(idx) {
            currentIdx = idx;
            render();
            lightbox.hidden = false;
            lightbox.setAttribute('aria-hidden', 'false');
            document.body.classList.add('lightbox-open');
            // Deferir un tick para que CSS active la transicion
            requestAnimationFrame(function () {
                lightbox.classList.add('is-visible');
            });
        }

        function close() {
            lightbox.classList.remove('is-visible');
            lightbox.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('lightbox-open');
            setTimeout(function () { lightbox.hidden = true; }, 200);
        }

        function render() {
            var item = gallery[currentIdx];
            if (!item) return;
            img.src = item.src;
            img.alt = item.alt;
            caption.innerHTML = item.caption;
        }

        function prev() {
            currentIdx = (currentIdx - 1 + gallery.length) % gallery.length;
            render();
        }

        function next() {
            currentIdx = (currentIdx + 1) % gallery.length;
            render();
        }

        cards.forEach(function (card, idx) {
            card.addEventListener('click', function () { open(idx); });
            // Accesibilidad teclado
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'button');
            card.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    open(idx);
                }
            });
        });

        btnClose.addEventListener('click', close);
        btnPrev.addEventListener('click', prev);
        btnNext.addEventListener('click', next);

        // Hero player: click o Enter/Space abre la captura activa en grande
        if (heroPlayer) {
            heroPlayer.addEventListener('click', function (e) {
                // No abrir cuando se clickea un boton interno (pausa, dots)
                if (e.target.closest('.hero__player-bar')) return;
                openHeroActive();
            });
            heroPlayer.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    if (e.target.closest('.hero__player-bar')) return;
                    e.preventDefault();
                    openHeroActive();
                }
            });
        }

        // Click fuera del frame -> cerrar
        lightbox.addEventListener('click', function (e) {
            if (e.target === lightbox) close();
        });

        // Teclado
        document.addEventListener('keydown', function (e) {
            if (lightbox.hidden) return;
            if (e.key === 'Escape') close();
            else if (e.key === 'ArrowLeft') prev();
            else if (e.key === 'ArrowRight') next();
        });
    }

    // =====================================================================
    // 3. Scroll reveal (fade-in on scroll)
    // =====================================================================
    function initReveal() {
        var els = document.querySelectorAll('.reveal');
        if (!els.length) return;
        if (!('IntersectionObserver' in window)) {
            els.forEach(function (e) { e.classList.add('is-visible'); });
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry, idx) {
                if (entry.isIntersecting) {
                    // Pequeño stagger para que aparezcan en cadena
                    var delay = (entry.target.dataset.revealDelay || idx * 40);
                    setTimeout(function () {
                        entry.target.classList.add('is-visible');
                    }, Math.min(delay, 200));
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
        els.forEach(function (el) { io.observe(el); });
    }

    // =====================================================================
    // 4. Sticky nav shadow on scroll
    // =====================================================================
    function initNav() {
        var nav = document.querySelector('.nav');
        if (!nav) return;
        var last = -1;
        function onScroll() {
            var scrolled = window.scrollY > 8;
            if (scrolled !== last) {
                nav.classList.toggle('is-scrolled', scrolled);
                last = scrolled;
            }
        }
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    // =====================================================================
    // Bootstrap
    // =====================================================================
    function bootstrap() {
        initHeroPlayer();
        initLightbox();
        initReveal();
        initNav();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootstrap);
    } else {
        bootstrap();
    }
})();
