
// Dynasty FC homepage and dashboard JavaScript
const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', () => {
    // NAVBAR SCROLL
    const navbar = document.getElementById('navbar');

    if (navbar) {
        const update = () => {
            navbar.classList.toggle('scrolled', window.scrollY > 40);
        };

        update();
        window.addEventListener('scroll', update, { passive: true });
    }

    // MOBILE NAVIGATION
    const toggle = document.getElementById('menuToggle');
    const menu = document.getElementById('navMenu');

    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            const open = menu.classList.toggle('open');

            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute(
                'aria-label',
                open ? 'Close navigation' : 'Open navigation'
            );

            toggle.innerHTML = open
                ? '<i class="fas fa-times"></i>'
                : '<i class="fas fa-bars"></i>';
        });

        menu.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', () => {
                menu.classList.remove('open');
                toggle.setAttribute('aria-expanded', 'false');
                toggle.setAttribute('aria-label', 'Open navigation');
                toggle.innerHTML = '<i class="fas fa-bars"></i>';
            });
        });
    }

    // REVEAL ANIMATIONS
    const reveals = document.querySelectorAll('.reveal');

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });

        reveals.forEach(el => observer.observe(el));
    } else {
        reveals.forEach(el => el.classList.add('active'));
    }

    // ANIMATED STATISTICS
    function animateCounter(el) {
        const target = Number.parseInt(el.dataset.target, 10);
        const suffix = el.dataset.suffix || '';

        if (!Number.isFinite(target)) return;

        const start = performance.now();
        const duration = 1600;

        function tick(now) {
            const progress = Math.min(
                (now - start) / duration,
                1
            );

            const eased = 1 - Math.pow(1 - progress, 3);

            el.textContent =
                Math.floor(target * eased) + suffix;

            if (progress < 1) {
                requestAnimationFrame(tick);
            } else {
                el.textContent = target + suffix;
            }
        }

        requestAnimationFrame(tick);
    }

    const counters = document.querySelectorAll(
        '.stat-number[data-target]'
    );

    if ('IntersectionObserver' in window) {
        const counterObserver = new IntersectionObserver(
            (entries, obs) => {
                entries.forEach(entry => {
                    if (
                        entry.isIntersecting &&
                        !entry.target.dataset.done
                    ) {
                        entry.target.dataset.done = 'true';
                        animateCounter(entry.target);
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.5 }
        );

        counters.forEach(el => counterObserver.observe(el));
    } else {
        counters.forEach(el => {
            el.textContent =
                (el.dataset.target || '0') +
                (el.dataset.suffix || '');
        });
    }

    // TESTIMONIAL CAROUSEL
    const testimonials = [
        ...document.querySelectorAll('.testimonial-card')
    ];

    const dots = document.getElementById('testimonialDots');
    let current = 0;

    function showTestimonial(index) {
        if (!testimonials.length) return;

        current =
            (index + testimonials.length) % testimonials.length;

        testimonials.forEach((el, i) => {
            el.classList.toggle('active', i === current);
        });

        if (dots) {
            [...dots.children].forEach((dot, i) => {
                dot.classList.toggle('active', i === current);
                dot.setAttribute(
                    'aria-pressed',
                    String(i === current)
                );
            });
        }
    }

    if (dots && testimonials.length) {
        testimonials.forEach((_, index) => {
            const button = document.createElement('button');

            button.type = 'button';
            button.className =
                'testimonial-dot' +
                (index === 0 ? ' active' : '');

            button.setAttribute(
                'aria-label',
                `Show testimonial ${index + 1}`
            );

            button.setAttribute(
                'aria-pressed',
                String(index === 0)
            );

            button.addEventListener('click', () => {
                showTestimonial(index);
            });

            dots.appendChild(button);
        });

        if (testimonials.length > 1) {
            setInterval(() => {
                showTestimonial(current + 1);
            }, 6000);
        }
    }

    // EXISTING DYNAMIC NEWS SUPPORT
    // The homepage now uses fixed highlight cards, so this
    // function only runs on pages that contain #newsGrid.
    loadDynamicNews();

    // DASHBOARD
    if (document.getElementById('dashboardCards')) {
        loadDashboard();
    }

    // PLAYERS
    if (document.getElementById('playersBody')) {
        loadPlayers();
    }

    // DONORS
    if (document.getElementById('donorsGrid')) {
        loadDonors();
    }
});


// DYNAMIC NEWS
async function loadDynamicNews() {
    const grid = document.getElementById('newsGrid');

    if (!grid) return;

    try {
        const response = await fetch(`${API_BASE}/newsletters`);

        if (!response.ok) {
            throw new Error('News request failed');
        }

        const news = await response.json();

        if (!Array.isArray(news) || !news.length) {
            return;
        }

        grid.replaceChildren();

        news.slice(0, 3).forEach(item => {
            const card = document.createElement('article');
            card.className = 'news-card reveal active';

            const img = document.createElement('img');
            img.src = item.image_url || '/images/team news.png';
            img.alt = item.title || 'Dynasty FC news';
            img.loading = 'lazy';

            const body = document.createElement('div');
            body.className = 'news-card-body';

            const heading = document.createElement('h3');
            heading.textContent = item.title || 'Club News';

            const paragraph = document.createElement('p');
            const content = item.content || '';

            paragraph.textContent =
                content.length > 120
                    ? content.slice(0, 120) + '...'
                    : content;

            const date = document.createElement('span');
            date.className = 'news-date';

            date.textContent = item.created_at
                ? new Date(item.created_at).toLocaleDateString(
                    'en-ZA',
                    {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric'
                    }
                )
                : 'Latest Update';

            body.append(heading, paragraph, date);
            card.append(img, body);
            grid.appendChild(card);
        });
    } catch (error) {
        console.log(
            'Using static news fallback:',
            error.message
        );
    }
}


// DASHBOARD
async function loadDashboard() {
    try {
        const responses = await Promise.all([
            fetch(`${API_BASE}/players`),
            fetch(`${API_BASE}/staff`),
            fetch(`${API_BASE}/teams`),
            fetch(`${API_BASE}/finance`)
        ]);

        if (responses.some(response => !response.ok)) {
            throw new Error('Dashboard API request failed');
        }

        const [players, staff, teams, finance] =
            await Promise.all(
                responses.map(response => response.json())
            );

        let income = 0;
        let expenses = 0;

        (Array.isArray(finance) ? finance : []).forEach(row => {
            income += Number.parseFloat(row.income || 0) || 0;
            expenses += Number.parseFloat(row.expenses || 0) || 0;
        });

        const cards = document.getElementById('dashboardCards');

        if (cards) {
            cards.innerHTML = `
                <div class="dash-card">
                    <h3>Players</h3>
                    <div class="number">
                        ${Array.isArray(players) ? players.length : 0}
                    </div>
                </div>

                <div class="dash-card">
                    <h3>Staff</h3>
                    <div class="number">
                        ${Array.isArray(staff) ? staff.length : 0}
                    </div>
                </div>

                <div class="dash-card">
                    <h3>Teams</h3>
                    <div class="number">
                        ${Array.isArray(teams) ? teams.length : 0}
                    </div>
                </div>

                <div class="dash-card">
                    <h3>Income</h3>
                    <div class="number">
                        R${income.toFixed(2)}
                    </div>
                </div>

                <div class="dash-card">
                    <h3>Expenses</h3>
                    <div class="number">
                        R${expenses.toFixed(2)}
                    </div>
                </div>

                <div class="dash-card">
                    <h3>Net</h3>
                    <div class="number">
                        R${(income - expenses).toFixed(2)}
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}


// PLAYERS
async function loadPlayers() {
    try {
        const response = await fetch(`${API_BASE}/players`);

        if (!response.ok) {
            throw new Error('Players request failed');
        }

        const players = await response.json();
        const tbody = document.getElementById('playersBody');

        if (tbody && Array.isArray(players)) {
            tbody.replaceChildren();

            players.forEach(player => {
                const row = document.createElement('tr');

                const values = [
                    `${player.first_name || ''} ${player.last_name || ''}`.trim(),
                    player.position || '-',
                    player.team_name || '-',
                    player.age || '-'
                ];

                values.forEach(value => {
                    const cell = document.createElement('td');
                    cell.textContent = value;
                    row.appendChild(cell);
                });

                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading players:', error);
    }
}


// DONORS
async function loadDonors() {
    try {
        const response = await fetch(`${API_BASE}/donors`);

        if (!response.ok) {
            throw new Error('Donors request failed');
        }

        const donors = await response.json();
        const grid = document.getElementById('donorsGrid');

        if (grid && Array.isArray(donors)) {
            grid.replaceChildren();

            donors.forEach(donor => {
                const card = document.createElement('div');
                card.className = 'donor-card';

                const icon = document.createElement('div');
                icon.className = 'donor-logo';
                icon.innerHTML =
                    '<i class="fas fa-handshake"></i>';

                const name = document.createElement('div');
                name.className = 'donor-name';
                name.textContent = donor.donor_name || 'Donor';

                const type = document.createElement('div');
                type.className = 'donor-type';
                type.textContent = donor.donor_type || '';

                const amount = document.createElement('div');
                amount.className = 'donor-amount';

                amount.textContent =
                    `R${(
                        Number.parseFloat(donor.total_amount || 0) || 0
                    ).toFixed(2)}`;

                card.append(icon, name, type, amount);

                card.addEventListener('click', () => {
                    viewDonor(donor.donor_name || '');
                });

                grid.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Error loading donors:', error);
    }
}

function viewDonor(name) {
    window.alert(`Viewing donor profile: ${name}`);
}