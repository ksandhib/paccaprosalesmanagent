/**
 * PaccaPro AI Sales Analysis System (PASAS)
 * Frontend SPA Core Controller with i18n English/Tamil support
 */

const API_ROOT = window.location.origin;

$(document).ready(function () {
    // Application State
    let authToken = localStorage.getItem("pasas_token") || "";
    let authUser = localStorage.getItem("pasas_username") || "";
    let charts = {}; // references to chart.js instances
    let analysisTable = null; // reference to DataTable
    let translations = {}; // active language dictionary mapping

    // Configure Ajax headers for secure JWT authentication
    $.ajaxSetup({
        beforeSend: function (xhr) {
            if (authToken) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            }
        },
        error: function (xhr) {
            if (xhr.status === 401) {
                logout();
            }
        }
    });

    // Initialize Theme Preference
    const savedTheme = localStorage.getItem("pasas_theme") || "light";
    if (savedTheme === "dark") {
        applyDarkTheme();
    } else {
        applyLightTheme();
    }

    // Initialize Language Preference (Bilingual i18n System)
    const savedLang = localStorage.getItem("pasas_lang") || "en";
    setLanguage(savedLang);

    // Initialize View State
    if (authToken) {
        showMainInterface();
    } else {
        showLoginScreen();
    }

    // Set default date input in Upload Page to Today
    const uploadDateEl = document.getElementById("upload-date");
    if (uploadDateEl) {
        uploadDateEl.valueAsDate = new Date();
    }

    // ==========================================
    // LANGUAGE SWITCHER (i18n IMPLEMENTATION)
    // ==========================================

    $("#lang-btn-en").on("click", function (e) {
        e.preventDefault();
        setLanguage("en");
    });

    $("#lang-btn-ta").on("click", function (e) {
        e.preventDefault();
        setLanguage("ta");
    });

    function setLanguage(lang) {
        localStorage.setItem("pasas_lang", lang);
        
        // Toggle switcher styling active states
        if (lang === "ta") {
            $("#lang-btn-ta").removeClass("text-muted").addClass("text-primary fw-bold");
            $("#lang-btn-en").removeClass("text-primary fw-bold").addClass("text-muted");
        } else {
            $("#lang-btn-en").removeClass("text-muted").addClass("text-primary fw-bold");
            $("#lang-btn-ta").removeClass("text-primary fw-bold").addClass("text-muted");
        }

        // Fetch local JSON dictionary mappings file
        $.getJSON(`translations/${lang}.json`, function (dict) {
            translations = dict;

            // 1. Translate standard tags text content
            $("[data-i18n]").each(function () {
                const key = $(this).data("i18n");
                if (translations[key]) {
                    $(this).html(translations[key]);
                }
            });

            // 2. Translate form inputs placeholder tags
            $("[data-i18n-placeholder]").each(function () {
                const key = $(this).data("i18n-placeholder");
                if (translations[key]) {
                    $(this).attr("placeholder", translations[key]);
                }
            });

            // 3. Translate page subheadings dynamically
            const activeView = $(".menu-item.active").data("target") || "view-dashboard";
            updatePageHeaderLabels(activeView);

            // Re-apply correct theme toggle button label after translation scan
            if ($("body").hasClass("dark-theme")) {
                $("#theme-toggle-text").text(translations["theme_light"] || "Light Mode");
            } else {
                $("#theme-toggle-text").text(translations["theme_night"] || "Night Mode");
            }

            // Re-render dashboard stats to apply localization in tables/charts
            if ($("#view-dashboard").is(":visible")) {
                loadDashboardData();
            }

            // Localize DataTable if initialized
            if ($("#view-analysis").is(":visible")) {
                loadAnalysisDataTable();
            }
        }).fail(function () {
            console.error("Failed to load language files dictionary for: " + lang);
        });
    }

    function updatePageHeaderLabels(viewId) {
        let titleKey = "menu_dashboard";
        let subKey = "dash_subtitle";

        if (viewId === "view-analysis") {
            titleKey = "menu_analysis";
            subKey = "analysis_subtitle";
        } else if (viewId === "view-poster-analysis") {
            titleKey = "menu_poster_analysis";
            subKey = "poster_subtitle";
        } else if (viewId === "view-sync") {
            titleKey = "menu_sync";
            subKey = "sync_subtitle";
        } else if (viewId === "view-assistant") {
            titleKey = "menu_assistant";
            subKey = "assistant_subtitle";
        }

        if (translations[titleKey]) $("#current-page-title").text(translations[titleKey]);
        if (viewId === "view-sync") $("#current-page-title").text("Upload");
        if (translations[subKey]) $("#current-page-subtitle").text(translations[subKey]);
    }

    // ==========================================
    // AUTHENTICATION LOGIC
    // ==========================================

    $("#login-form").on("submit", function (e) {
        e.preventDefault();
        const username = $("#username").val().trim();
        const password = $("#password").val().trim();
        const errorAlert = $("#login-error-msg");

        errorAlert.addClass("d-none").text("");

        $.ajax({
            url: `${API_ROOT}/login`,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ username, password }),
            success: function (response) {
                authToken = response.access_token;
                authUser = response.username;
                localStorage.setItem("pasas_token", authToken);
                localStorage.setItem("pasas_username", authUser);
                
                showMainInterface();
            },
            error: function (xhr) {
                let errDetail = translations["login_failed"] || "Failed to connect to the backend server.";
                if (xhr.responseJSON && xhr.responseJSON.detail) {
                    errDetail = xhr.responseJSON.detail;
                }
                errorAlert.removeClass("d-none").text(errDetail);
            }
        });
    });

    $(".logout-btn").on("click", function () {
        logout();
    });

    function logout() {
        authToken = "";
        authUser = "";
        localStorage.removeItem("pasas_token");
        localStorage.removeItem("pasas_username");
        showLoginScreen();
    }

    function showLoginScreen() {
        $("#main-interface").addClass("d-none");
        $("#login-screen").removeClass("d-none");
    }

    function showMainInterface() {
        $("#login-screen").addClass("d-none");
        $("#main-interface").removeClass("d-none");
        $("#logged-user-display").text(authUser);
        
        navigateTo("view-dashboard");
    }

    // ==========================================
    // NAVIGATION / ROUTING LOGIC
    // ==========================================

    $(".menu-item").on("click", function (e) {
        e.preventDefault();
        const targetView = $(this).data("target");

        // Toggle active menu class
        $(".menu-item").removeClass("active");
        $(this).addClass("active");

        navigateTo(targetView);
    });

    function navigateTo(viewId) {
        updatePageHeaderLabels(viewId);

        $(".content-section").addClass("d-none");
        $(`#${viewId}`).removeClass("d-none");

        // Load specific view data
        if (viewId === "view-dashboard") {
            loadDashboardData();
        } else if (viewId === "view-analysis") {
            loadAnalysisDataTable();
            loadFilterRepresentatives();
        } else if (viewId === "view-poster-analysis") {
            loadPosterDashboard();
        } else if (viewId === "view-sync") {
            loadSyncDashboard();
            loadSyncHistory();
            if (typeof updateManualClientDropdown === "function") {
                updateManualClientDropdown($("#manual-rep-select").val() || "Sankarapandian");
            }
        } else if (viewId === "view-assistant") {
            loadChatHistory();
        }
    }

    // ==========================================
    // VIEW 1: DASHBOARD DATA INGESTION
    // ==========================================

    function loadDashboardData() {
        $.ajax({
            url: `${API_ROOT}/dashboard`,
            type: "GET",
            success: function (res) {
                $("#card-total-reports").text(res.cards.total_reports);
                $("#card-today-reports").text(res.cards.today_reports);
                $("#card-weekly-reports").text(res.cards.weekly_reports);
                $("#card-monthly-reports").text(res.cards.monthly_reports);
                $("#card-yearly-reports").text(res.cards.yearly_reports);
                
                const repBody = $("#rep-performance-body");
                repBody.empty();
                if (res.rep_table.length === 0) {
                    const emptyText = translations["no_rep_data"] || "No representative data available. Please upload voice recordings.";
                    repBody.append(`<tr><td colspan="5" class="text-center text-muted">${emptyText}</td></tr>`);
                } else {
                    res.rep_table.forEach(row => {
                        const fmt = val => (!val || val === 0) ? '<span class="text-muted">-</span>' : `₹${Math.round(val).toLocaleString("en-IN")}`;
                        repBody.append(`
                            <tr>
                                <td><strong>${row.representative}</strong></td>
                                <td>${fmt(row.today_performance)}</td>
                                <td>${fmt(row.weekly_performance)}</td>
                                <td>${fmt(row.monthly_performance)}</td>
                                <td>${fmt(row.yearly_performance)}</td>
                            </tr>
                        `);
                    });
                }

                renderDashboardCharts(res.charts);
                loadRankingData(currentRankingPeriod);
                loadMasterDealers();
            },
            error: function (xhr) {
                console.error("Dashboard loading failed", xhr);
            }
        });
    }

    let repRankingChart = null;
    let repEmotionChart = null;

    function loadRankingData(period = "all", startDate = null, endDate = null) {
        currentRankingPeriod = period;
        let url = `${API_ROOT}/dashboard/ranking?period=${period}`;
        if (period === "custom" && startDate && endDate) {
            url += `&start_date=${startDate}&end_date=${endDate}`;
        }
        $.ajax({
            url: url,
            type: "GET",
            beforeSend: function(xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function (res) {
                cachedRankingData = res;
                renderOverallSentimentRankingTable(res);
                renderRankingTable(res);
                renderRankingCharts(res);
            },
            error: function (xhr) {
                console.error("Failed to load ranking data", xhr);
            }
        });
    }

    function renderRankingCharts(rankingData) {
        if (!rankingData || rankingData.length === 0) return;

        const fontColor = "#94a3b8";
        const gridColor = "rgba(148, 163, 184, 0.1)";

        const labels = rankingData.map(r => r.representative);
        const starsData = rankingData.map(r => r.total_stars);

        const posData = rankingData.map(r => r.sentiment_positive || 0);
        const neuData = rankingData.map(r => r.sentiment_medium || 0);
        const negData = rankingData.map(r => r.sentiment_notgood || 0);

        // Chart 1: Performance Ranking Pie Chart
        const ctx1 = document.getElementById("chart-rep-performance-ranking");
        if (ctx1) {
            if (repRankingChart) repRankingChart.destroy();

            const pieColors = [
                "#f59e0b", "#3b82f6", "#10b981", "#8b5cf6", 
                "#ec4899", "#6366f1", "#06b6d4", "#14b8a6"
            ];

            repRankingChart = new Chart(ctx1, {
                type: "pie",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Total Stars (Max 50)",
                        data: starsData,
                        backgroundColor: pieColors.slice(0, labels.length),
                        borderColor: "#1e293b",
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: "right",
                            labels: { color: fontColor, font: { size: 12, weight: "bold" } }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => ` ${ctx.label}: ${ctx.raw} / 50 Stars`
                            }
                        }
                    }
                }
            });
        }

        // Chart 2: Emotion Tracking Bar Chart (Grouped)
        const ctx2 = document.getElementById("chart-rep-emotion-tracking");
        if (ctx2) {
            if (repEmotionChart) repEmotionChart.destroy();
            repEmotionChart = new Chart(ctx2, {
                type: "bar",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: "🟢 Positive",
                            data: posData,
                            backgroundColor: "#10b981",
                            borderRadius: 4
                        },
                        {
                            label: "🟡 Neutral",
                            data: neuData,
                            backgroundColor: "#f59e0b",
                            borderRadius: 4
                        },
                        {
                            label: "🔴 Negative",
                            data: negData,
                            backgroundColor: "#ef4444",
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "top",
                            labels: { color: fontColor, font: { weight: "bold" } }
                        }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: "#ffffff", font: { weight: "bold" } } },
                        y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: fontColor, precision: 0 } }
                    }
                }
            });
        }
    }

    function renderOverallSentimentRankingTable(data) {
        const body = $("#rep-sentiment-ranking-body");
        body.empty();
        
        if (!data || data.length === 0) {
            body.append(`<tr><td colspan="13" class="text-center text-muted">No overall sentiment performance data available yet.</td></tr>`);
            return;
        }

        const renderRankBadge = (rank) => {
            if (rank === 1) return "🏆 1st";
            if (rank === 2) return "🥈 2nd";
            if (rank === 3) return "🥉 3rd";
            return `${rank}th`;
        };

        const getLevelBadgeClass = (level) => {
            if (level === "Excellent") return "bg-success text-white";
            if (level === "Very Good") return "bg-info text-dark";
            if (level === "Good") return "bg-primary text-white";
            if (level === "Needs Improvement") return "bg-warning text-dark";
            return "bg-danger text-white";
        };

        const renderSentimentBadge = (sent) => {
            if (sent === "Positive") return `<span class="badge bg-success-subtle text-success border border-success text-nowrap"><i class="bi bi-circle-fill text-success me-1 tiny"></i>🟢 Positive</span>`;
            if (sent === "Neutral") return `<span class="badge bg-warning-subtle text-warning border border-warning text-nowrap"><i class="bi bi-circle-fill text-warning me-1 tiny"></i>🟡 Neutral</span>`;
            if (sent === "Negative") return `<span class="badge bg-danger-subtle text-danger border border-danger text-nowrap"><i class="bi bi-circle-fill text-danger me-1 tiny"></i>🔴 Negative</span>`;
            return `<span class="text-muted">-</span>`;
        };

        data.forEach(row => {
            const hasData = row.visits > 0;
            const percentageText = hasData ? `${row.percentage}%` : "-";
            const levelText = hasData ? row.level : "No Data";
            const ts = row.topic_sentiments || {};

            const salesSent = hasData ? renderSentimentBadge(ts.sales) : `<span class="text-muted">-</span>`;
            const collSent = hasData ? renderSentimentBadge(ts.collection) : `<span class="text-muted">-</span>`;
            const compSent = hasData ? renderSentimentBadge(ts.competition) : `<span class="text-muted">-</span>`;
            const prodSent = hasData ? renderSentimentBadge(ts.product) : `<span class="text-muted">-</span>`;
            const priceSent = hasData ? renderSentimentBadge(ts.price_list) : `<span class="text-muted">-</span>`;
            const servSent = hasData ? renderSentimentBadge(ts.our_services) : `<span class="text-muted">-</span>`;
            const newpSent = hasData ? renderSentimentBadge(ts.our_new_products) : `<span class="text-muted">-</span>`;
            const msSent = hasData ? renderSentimentBadge(ts.most_sell_products) : `<span class="text-muted">-</span>`;
            const stockSent = hasData ? renderSentimentBadge(ts.pending_stock) : `<span class="text-muted">-</span>`;
            const fupSent = hasData ? renderSentimentBadge(ts.follow_up_date) : `<span class="text-muted">-</span>`;

            body.append(`
                <tr class="rep-ranking-row rep-sentiment-ranking-row" data-rep="${row.representative}" style="cursor: pointer;">
                    <td><strong>${renderRankBadge(row.rank)}</strong></td>
                    <td><strong class="text-white">${row.representative}</strong></td>
                    <td>${salesSent}</td>
                    <td>${collSent}</td>
                    <td>${compSent}</td>
                    <td>${prodSent}</td>
                    <td>${priceSent}</td>
                    <td>${servSent}</td>
                    <td>${newpSent}</td>
                    <td>${msSent}</td>
                    <td>${stockSent}</td>
                    <td>${fupSent}</td>
                    <td><span class="badge ${getLevelBadgeClass(row.level)}">${levelText} (${percentageText})</span></td>
                </tr>
            `);
        });
    }

    function renderRankingTable(data) {
        const body = $("#rep-ranking-body");
        body.empty();
        
        if (data.length === 0) {
            body.append(`<tr><td colspan="14" class="text-center text-muted">No performance data available yet.</td></tr>`);
            return;
        }

        const renderStars = (score) => {
            const fullStars = Math.round(score);
            let stars = "";
            for (let i = 1; i <= 5; i++) {
                stars += i <= fullStars ? "★" : "☆";
            }
            return `<span class="text-warning text-nowrap">${stars}</span>`;
        };

        const renderRankBadge = (rank) => {
            if (rank === 1) return "🏆 1st";
            if (rank === 2) return "🥈 2nd";
            if (rank === 3) return "🥉 3rd";
            return `${rank}th`;
        };

        const getLevelBadgeClass = (level) => {
            if (level === "Excellent") return "bg-success text-white";
            if (level === "Very Good") return "bg-info text-dark";
            if (level === "Good") return "bg-primary text-white";
            if (level === "Needs Improvement") return "bg-warning text-dark";
            return "bg-danger text-white";
        };

        data.forEach(row => {
            const hasData = row.visits > 0;
            const levelBadge = hasData 
                ? `<span class="badge ${getLevelBadgeClass(row.level)}">${row.level} (${row.percentage}%)</span>` 
                : `<span class="badge bg-secondary">-</span>`;
            
            const salesStars = hasData ? renderStars(row.scores.sales) : `<span class="text-muted">-</span>`;
            const collStars = hasData ? renderStars(row.scores.collection) : `<span class="text-muted">-</span>`;
            const compStars = hasData ? renderStars(row.scores.competition) : `<span class="text-muted">-</span>`;
            const prodStars = hasData ? renderStars(row.scores.product) : `<span class="text-muted">-</span>`;
            const priceStars = hasData ? renderStars(row.scores.price_list) : `<span class="text-muted">-</span>`;
            const servStars = hasData ? renderStars(row.scores.our_services) : `<span class="text-muted">-</span>`;
            const newpStars = hasData ? renderStars(row.scores.our_new_products) : `<span class="text-muted">-</span>`;
            const msStars = hasData ? renderStars(row.scores.most_sell_products) : `<span class="text-muted">-</span>`;
            const stockStars = hasData ? renderStars(row.scores.pending_stock) : `<span class="text-muted">-</span>`;
            const fupStars = hasData ? renderStars(row.scores.follow_up_date) : `<span class="text-muted">-</span>`;
            const totalStarsDisplay = hasData ? `<strong class="text-warning">${row.total_stars} ★</strong>` : `<span class="text-muted">-</span>`;

            body.append(`
                <tr class="rep-ranking-row" data-rep="${row.representative}" style="cursor: pointer;">
                    <td><strong>${renderRankBadge(row.rank)}</strong></td>
                    <td><strong class="text-white">${row.representative}</strong></td>
                    <td>${salesStars}</td>
                    <td>${collStars}</td>
                    <td>${compStars}</td>
                    <td>${prodStars}</td>
                    <td>${priceStars}</td>
                    <td>${servStars}</td>
                    <td>${newpStars}</td>
                    <td>${msStars}</td>
                    <td>${stockStars}</td>
                    <td>${fupStars}</td>
                    <td>${totalStarsDisplay}</td>
                    <td>${levelBadge}</td>
                    <td>
                        <div class="d-flex flex-wrap gap-1">
                            ${(() => {
                                if (!hasData) return `<span class="text-muted small">-</span>`;
                                let html = "";
                                if (row.sentiment_positive > 0) {
                                    html += `<span class="tag-badge tag-sent-positive text-nowrap">Positive: ${row.sentiment_positive}</span>`;
                                }
                                if (row.sentiment_medium > 0) {
                                    html += `<span class="tag-badge tag-sent-medium text-nowrap">Medium: ${row.sentiment_medium}</span>`;
                                }
                                if (row.sentiment_notgood > 0) {
                                    html += `<span class="tag-badge tag-sent-not-good text-nowrap">Not Good: ${row.sentiment_notgood}</span>`;
                                }
                                return html || `<span class="text-muted small">-</span>`;
                            })()}
                        </div>
                    </td>
                </tr>
            `);
        });
    }

    /* =========================================================================
       MASTER DEALERS DIRECTORY & SEARCH FILTERS SYSTEM
       ========================================================================= */

    let masterDealersData = null;

    function loadMasterDealers(callback) {
        $.ajax({
            url: `${API_ROOT}/dealers`,
            type: "GET",
            success: function(res) {
                if (res.status === "success") {
                    masterDealersData = res.dealers;
                    $("#total-master-dealers-count").text(`Total Master Dealers: ${res.total_dealers.toLocaleString("en-IN")}`);
                    renderMasterDealerDirectory(res.dealers, res.counts);
                    
                    const currentRep = $("#search-sales-rep").val() || "all";
                    updateDealerDropdown(currentRep);
                    if (typeof callback === "function") callback();
                }
            },
            error: function(err) {
                console.error("Failed to load dealers master data", err);
            }
        });
    }

    function updateDealerDropdown(selectedRep) {
        if (!masterDealersData) {
            loadMasterDealers(function() {
                updateDealerDropdown(selectedRep);
            });
            return;
        }

        const dealerSelect = $("#search-dealer-name");
        dealerSelect.empty();
        dealerSelect.append(`<option value="all" selected>All Dealers</option>`);

        const repMapping = {
            "balamurugan": "Balamurugan",
            "rajeshwaran": "Rajeshwaran",
            "sriram": "Sriram",
            "vinothkumar": "Vinothkumar",
            "parthiban": "Parthiban",
            "periyarselvam": "Periyar Selvam",
            "sankarapandian": "Sankarapandian"
        };

        let dealersToDisplay = [];

        if (selectedRep && selectedRep !== "all") {
            const normSelected = (selectedRep || "").toLowerCase().replace(/[\s\-_]/g, "");
            const exactKey = repMapping[normSelected];

            if (exactKey && masterDealersData[exactKey]) {
                dealersToDisplay = [...masterDealersData[exactKey]];
            } else if (masterDealersData[selectedRep]) {
                dealersToDisplay = [...masterDealersData[selectedRep]];
            }
        } else {
            Object.values(masterDealersData).forEach(list => {
                dealersToDisplay = dealersToDisplay.concat(list);
            });
        }

        // Deduplicate and sort dealers alphabetically
        dealersToDisplay = Array.from(new Set(dealersToDisplay)).sort();

        dealersToDisplay.forEach(d => {
            dealerSelect.append(`<option value="${d}">${d}</option>`);
        });

        dealerSelect.val("all");
    }

    function renderMasterDealerDirectory(dealersMap, countsMap) {
        const accordion = $("#dealerDirectoryAccordion");
        accordion.empty();

        const reps = [
            "Balamurugan",
            "Rajeshwaran",
            "Sriram",
            "Vinothkumar",
            "Parthiban",
            "Periyar Selvam",
            "Sankarapandian"
        ];

        reps.forEach((rep, index) => {
            const list = dealersMap[rep] || [];
            const count = countsMap[rep] || list.length;
            const collapseId = `collapse-rep-${index}`;
            const headerId = `heading-rep-${index}`;
            const searchInputId = `search-dealer-input-${index}`;
            const containerId = `dealer-list-container-${index}`;

            accordion.append(`
                <div class="accordion-item bg-dark border-secondary text-white mb-2 rounded overflow-hidden">
                    <h2 class="accordion-header" id="${headerId}">
                        <button class="accordion-button collapsed bg-dark text-white fw-bold shadow-none" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="false" aria-controls="${collapseId}">
                            <i class="bi bi-person-badge text-primary me-2"></i> ${rep} 
                            <span class="badge bg-secondary ms-3">Total Dealers: ${count}</span>
                        </button>
                    </h2>
                    <div id="${collapseId}" class="accordion-collapse collapse" aria-labelledby="${headerId}" data-bs-parent="#dealerDirectoryAccordion">
                        <div class="accordion-body bg-dark text-white">
                            <div class="mb-3">
                                <input type="text" class="form-control form-control-sm table-filter-input text-white dealer-live-search" id="${searchInputId}" data-container="${containerId}" placeholder="Search dealer in ${rep} list...">
                            </div>
                            <div id="${containerId}" class="dealer-cards-grid p-1" style="max-height: 400px; overflow-y: auto;">
                                ${renderDealerItemsHtml(list)}
                            </div>
                        </div>
                    </div>
                </div>
            `);
        });
    }

    function renderDealerItemsHtml(dealerList) {
        if (!dealerList || dealerList.length === 0) {
            return `<div class="text-muted small py-2">No dealers available for this representative.</div>`;
        }
        let html = `<div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 g-2">`;
        dealerList.forEach(d => {
            const cleanD = d.replace(/"/g, '&quot;');
            html += `
                <div class="col dealer-item-node" data-dealer="${d.toLowerCase()}">
                    <div class="p-2 rounded bg-secondary bg-opacity-10 border border-secondary border-opacity-25 h-100 d-flex align-items-center gap-2">
                        <i class="bi bi-shop text-info"></i>
                        <span class="tiny text-white text-truncate" title="${cleanD}">${cleanD}</span>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
        return html;
    }

    function applySearchFilters() {
        const startDate = $("#search-start-date").val();
        const endDate = $("#search-end-date").val();
        const selectedRep = $("#search-sales-rep").val();
        const selectedDealer = $("#search-dealer-name").val();

        // Sync with performance ranking cards
        if (startDate && endDate) {
            loadRankingData("custom", startDate, endDate);
        } else if (!startDate && !endDate) {
            loadRankingData("all");
        }

        // Filter analysis DataTable if initialized
        if (analysisTable) {
            analysisTable.draw();
        }
    }

    // Custom DataTable Filter for Search Filters Card
    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
        if (settings.nTable.id !== "analysis-datatable") return true;

        const startDate = $("#search-start-date").val();
        const endDate = $("#search-end-date").val();
        const selectedRep = $("#search-sales-rep").val();
        const selectedDealer = $("#search-dealer-name").val();

        const rowDate = data[1] || ""; // Date column
        const rowRep = data[2] || "";  // Sales Rep column
        const rowDealer = data[3] || ""; // Dealer Name column

        if (startDate && rowDate && rowDate < startDate) return false;
        if (endDate && rowDate && rowDate > endDate) return false;
        if (selectedRep && selectedRep !== "all" && !rowRep.toLowerCase().includes(selectedRep.toLowerCase())) return false;
        if (selectedDealer && selectedDealer !== "all" && !rowDealer.toLowerCase().includes(selectedDealer.toLowerCase())) return false;

        return true;
    });

    function loadFilteredPerformance() {
        const startDate = $("#search-start-date").val();
        const endDate = $("#search-end-date").val();
        const selectedRep = $("#search-sales-rep").val();
        const selectedDealer = $("#search-dealer-name").val();

        let url = `${API_ROOT}/dashboard/filtered-performance?sales_rep=${encodeURIComponent(selectedRep)}&dealer_name=${encodeURIComponent(selectedDealer)}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;

        $("#btn-show-performance").prop("disabled", true).html(`<span class="spinner-border spinner-border-sm me-1"></span> Analyzing performance...`);

        $.ajax({
            url: url,
            type: "GET",
            success: function(res) {
                $("#btn-show-performance").prop("disabled", false).html(`<i class="bi bi-bar-chart-line me-1"></i> Show Performance`);
                if (res.status === "success") {
                    renderFilteredPerformanceView(res);
                    $("#show-perf-prompt-banner").addClass("d-none");
                    $("#filtered-performance-container").removeClass("d-none");
                    $('html, body').animate({
                        scrollTop: $("#filtered-performance-container").offset().top - 100
                    }, 500);
                } else {
                    alert("Unable to load performance data. Please try again.");
                }
            },
            error: function(err) {
                $("#btn-show-performance").prop("disabled", false).html(`<i class="bi bi-bar-chart-line me-1"></i> Show Performance`);
                console.error("Failed to load filtered performance", err);
                alert("Unable to load performance data. Please try again.");
            }
        });
    }

    function renderFilteredPerformanceView(data) {
        // 1. Header
        $("#header-perf-rep").text(data.header.sales_rep);
        $("#header-perf-dealer").text(data.header.dealer);
        $("#header-perf-dates").text(data.header.date_range);
        $("#header-perf-count").text(`${data.count} Conversations`);

        // 2. Overall Performance & Emotion
        $("#overall-score-stars").text(data.overall_stars || "☆☆☆☆☆");
        $("#overall-score-num").text(data.overall_score.toFixed(1));

        const renderEmotionBadge = (sent) => {
            if (sent === "Positive") return `<span class="badge bg-success fs-6 px-4 py-2"><i class="bi bi-emoji-smile me-2"></i>🟢 Positive</span>`;
            if (sent === "Neutral") return `<span class="badge bg-warning text-dark fs-6 px-4 py-2"><i class="bi bi-emoji-neutral me-2"></i>🟡 Neutral</span>`;
            if (sent === "Negative") return `<span class="badge bg-danger fs-6 px-4 py-2"><i class="bi bi-emoji-frown me-2"></i>🔴 Negative</span>`;
            return `<span class="badge bg-secondary fs-6 px-4 py-2">-</span>`;
        };

        $("#overall-emotion-badge").html(renderEmotionBadge(data.overall_sentiment));

        // 3. 10 Performance Topics Table
        const topicsBody = $("#filtered-topics-body");
        topicsBody.empty();

        const topicLabels = {
            "sales": "Sales",
            "collection": "Collection",
            "competition": "Competition",
            "product": "Product",
            "price_list": "Price List",
            "our_services": "Our Services",
            "our_new_products": "Our New Products",
            "most_sell_products": "Most Sell Products",
            "pending_stock": "Pending Stock",
            "follow_up_date": "Follow-Up Date"
        };

        const renderTopicEmotionBadge = (sent) => {
            if (sent === "Positive") return `<span class="badge bg-success-subtle text-success border border-success text-nowrap">🟢 Positive</span>`;
            if (sent === "Neutral") return `<span class="badge bg-warning-subtle text-warning border border-warning text-nowrap">🟡 Neutral</span>`;
            if (sent === "Negative") return `<span class="badge bg-danger-subtle text-danger border border-danger text-nowrap">🔴 Negative</span>`;
            return `<span class="text-muted">-</span>`;
        };

        if (!data.topics || Object.keys(data.topics).length === 0 || data.count === 0) {
            topicsBody.append(`<tr><td colspan="4" class="text-center text-muted py-4">No conversation data available for the selected filters.</td></tr>`);
        } else {
            Object.keys(topicLabels).forEach(key => {
                const item = data.topics[key] || { stars: "☆☆☆☆☆", sentiment: "-", explanation: "No discussion logged." };
                const label = topicLabels[key];
                topicsBody.append(`
                    <tr>
                        <td><strong class="text-white">${label}</strong></td>
                        <td><span class="text-warning text-nowrap">${item.stars}</span> (${item.score.toFixed(1)})</td>
                        <td>${renderTopicEmotionBadge(item.sentiment)}</td>
                        <td class="text-muted small">${item.explanation}</td>
                    </tr>
                `);
            });
        }

        // 4. Filtered Conversations Table
        const convBody = $("#filtered-conversations-body");
        convBody.empty();

        if (!data.reports || data.reports.length === 0) {
            convBody.append(`<tr><td colspan="6" class="text-center text-muted py-4">No conversation records found matching the selected parameters.</td></tr>`);
        } else {
            data.reports.forEach(r => {
                const renderSentTag = (s) => {
                    if (s === "Positive") return `<span class="badge bg-success-subtle text-success border border-success">Positive</span>`;
                    if (s === "Negative" || s === "Not Good") return `<span class="badge bg-danger-subtle text-danger border border-danger">Negative</span>`;
                    return `<span class="badge bg-warning-subtle text-warning border border-warning">Neutral</span>`;
                };

                convBody.append(`
                    <tr>
                        <td class="text-nowrap">${r.date}</td>
                        <td><strong class="text-white">${r.sales_representative}</strong></td>
                        <td>${r.dealer_name}</td>
                        <td>${renderSentTag(r.sentiment)}</td>
                        <td class="small">${r.summary}</td>
                        <td class="tiny text-muted">${r.topics || "-"}</td>
                    </tr>
                `);
            });
        }
    }

    // Event Handlers for Search Filters
    $(document).on("click", "#btn-show-performance", function() {
        loadFilteredPerformance();
    });

    $(document).on("change", "#search-sales-rep", function() {
        const selectedRep = $(this).val();
        updateDealerDropdown(selectedRep);
    });

    $(document).on("click", "#btn-clear-search-filters", function() {
        $("#search-start-date").val("");
        $("#search-end-date").val("");
        $("#search-sales-rep").val("all");
        updateDealerDropdown("all");
        $("#search-dealer-name").val("all");
        $("#filtered-performance-container").addClass("d-none");
        $("#show-perf-prompt-banner").removeClass("d-none");
        applySearchFilters();
    });

    $(document).on("input", ".dealer-live-search", function() {
        const query = $(this).val().toLowerCase().trim();
        const containerId = $(this).data("container");
        $(`#${containerId} .dealer-item-node`).each(function() {
            const dealerName = $(this).attr("data-dealer") || "";
            if (!query || dealerName.includes(query)) {
                $(this).removeClass("d-none");
            } else {
                $(this).addClass("d-none");
            }
        });
    });

    function handleCalendarDateChange() {
        const fromVal = $("#ranking-from-date").val() || $("#ranking-from-date-2").val();
        const toVal = $("#ranking-to-date").val() || $("#ranking-to-date-2").val();

        // Sync values across both ranking date pickers
        $("#ranking-from-date, #ranking-from-date-2").val(fromVal);
        $("#ranking-to-date, #ranking-to-date-2").val(toVal);

        if (fromVal && toVal) {
            if (toVal < fromVal) {
                alert("Invalid Date Range: End Date cannot be earlier than Start Date.");
                return;
            }
            loadRankingData("custom", fromVal, toVal);
        } else if (!fromVal && !toVal) {
            loadRankingData("all");
        }
    }

    $(document).on("change", "#ranking-from-date, #ranking-to-date, #ranking-from-date-2, #ranking-to-date-2", function() {
        handleCalendarDateChange();
    });

    $(document).on("click", "#btn-clear-ranking-dates, .btn-clear-ranking-dates-action", function() {
        $("#ranking-from-date, #ranking-from-date-2").val("");
        $("#ranking-to-date, #ranking-to-date-2").val("");
        loadRankingData("all");
    });

    // Row click handler for detailed modal
    $(document).on("click", ".rep-ranking-row", function() {
        const repName = $(this).data("rep");
        const repData = cachedRankingData.find(r => r.representative === repName);
        if (!repData) return;

        $("#ranking-modal-rep-name").text(repData.representative);
        $("#ranking-modal-level").text(repData.visits > 0 ? repData.level : "No Data");
        
        const levelClasses = ["bg-success", "bg-info", "bg-primary", "bg-warning", "bg-danger"];
        $("#ranking-modal-level").removeClass(levelClasses.join(" "));
        if (repData.visits > 0) {
            if (repData.level === "Excellent") $("#ranking-modal-level").addClass("bg-success text-white");
            else if (repData.level === "Very Good") $("#ranking-modal-level").addClass("bg-info text-dark");
            else if (repData.level === "Good") $("#ranking-modal-level").addClass("bg-primary text-white");
            else if (repData.level === "Needs Improvement") $("#ranking-modal-level").addClass("bg-warning text-dark");
            else $("#ranking-modal-level").addClass("bg-danger text-white");
        } else {
            $("#ranking-modal-level").addClass("bg-danger text-white");
        }

        const renderStars = (score) => {
            const fullStars = Math.round(score);
            let stars = "";
            for (let i = 1; i <= 5; i++) {
                stars += i <= fullStars ? "★" : "☆";
            }
            return `<span class="text-warning fs-5">${stars}</span>`;
        };

        const periodNameMap = {
            "all": "All Time",
            "today": "Today",
            "week": "This Week",
            "month": "This Month",
            "year": "This Year"
        };

        $("#ranking-modal-total-stars").text(`${repData.total_stars} ★ / 50 ★`);
        $("#ranking-modal-percentage").text(repData.visits > 0 ? `${repData.percentage}%` : "-");
        $("#ranking-modal-period").text(periodNameMap[currentRankingPeriod] || "All Time");
        $("#ranking-modal-visits").text(repData.visits);
        $("#ranking-modal-rank").text(repData.visits > 0 ? `#${repData.rank}` : "-");
        $("#ranking-modal-completed-cats").text(`${repData.completed_categories} / 10`);

        const catList = $("#ranking-modal-categories-list");
        catList.empty();

        const catNames = {
            "sales": "Sales",
            "collection": "Collection",
            "competition": "Competition",
            "product": "Product",
            "price_list": "Price List",
            "our_services": "Our Services",
            "our_new_products": "Our New Products",
            "most_sell_products": "Most Sell Products",
            "pending_stock": "Pending Stock",
            "follow_up_date": "Follow-up Date"
        };

        Object.keys(catNames).forEach(cat => {
            const hasData = repData.visits > 0;
            const starsHtml = hasData ? renderStars(repData.scores[cat]) : "☆☆☆☆☆";
            const expText = repData.explanations[cat] || `${catNames[cat]} information was not discussed.`;
            
            catList.append(`
                <div class="mb-3 p-3 bg-dark-tint-2 rounded border border-secondary-subtle">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong class="text-white">${catNames[cat]}</strong>
                        <div>${starsHtml}</div>
                    </div>
                    <p class="text-muted small m-0">${expText}</p>
                </div>
            `);
        });

        $("#repRankingDetailModal").modal("show");
    });

    function renderDashboardCharts(chartData) {
        Object.keys(charts).forEach(key => {
            if (charts[key]) charts[key].destroy();
        });

        // Styles matching light/dark theme variables
        const isDark = $("body").hasClass("dark-theme");
        const fontColor = isDark ? "#94a3b8" : "#475569";
        const gridColor = isDark ? "rgba(148, 163, 184, 0.08)" : "rgba(148, 163, 184, 0.15)";

        const chartOptionsBase = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: fontColor, font: { family: "Arial" } } }
            },
            scales: {
                x: { grid: { color: gridColor }, ticks: { color: fontColor } },
                y: { grid: { color: gridColor }, ticks: { color: fontColor } }
            }
        };

        // i18n chart dataset labels
        const salesLabel = translations["th_sales"] || "Booked Sales (INR)";
        const voiceFilesLabel = translations["label_file"] || "Voice Files Uploaded";
        const avgDurationLabel = translations["th_duration"] || "Avg Duration (sec)";
        const clientCountLabel = translations["filter_client"] || "Client count";

        const compElem = document.getElementById("chart-rep-comparison");
        if (compElem) {
            charts.repComparison = new Chart(compElem, {
                type: "doughnut",
                data: {
                    labels: chartData.rep_comparison.labels,
                    datasets: [{
                        data: chartData.rep_comparison.data,
                        backgroundColor: ["#2563eb", "#10b981", "#8b5cf6", "#ea580c", "#06b6d4", "#ef4444"],
                        borderWidth: 1,
                        borderColor: "#ffffff"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "right",
                            labels: { color: fontColor }
                        }
                    }
                }
            });
        }
    }


    // ==========================================
    // VIEW 2: AI ANALYSIS DATATABLE & EXPORTS
    // ==========================================

    function loadFilterRepresentatives() {
        $.ajax({
            url: `${API_ROOT}/sales-representatives`,
            type: "GET",
            success: function (reps) {
                const repSelect = $("#filter-rep");
                const allLabel = translations["btn_reset"] === "வடிகட்டிகளை மீட்டமை" ? "அனைத்து பிரதிநிதிகளும்" : "All Representatives";
                repSelect.empty().append(`<option value="">${allLabel}</option>`);
                reps.forEach(rep => {
                    repSelect.append(`<option value="${rep}">${rep}</option>`);
                });
            }
        });
    }

    function loadAnalysisDataTable() {
        if ($.fn.DataTable.isDataTable("#analysis-datatable")) {
            $("#analysis-datatable").DataTable().destroy();
        }

        $.ajax({
            url: `${API_ROOT}/reports`,
            type: "GET",
            success: function (reports) {
                const tbody = $("#analysis-datatable tbody");
                tbody.empty();
                
                reports.forEach(r => {
                    const sentValue = r.sentiment || 'Medium';
                    const sentimentClass = `tag-badge tag-sent-${sentValue.toLowerCase().replace(/\s+/g, '-')}`;
                    
                    function formatCell(val) {
                        if (!val || val === "None" || val === "N/A" || val === "null" || val === "undefined") return `<span class="text-muted">-</span>`;
                        const str = String(val).strip ? String(val).strip() : String(val);
                        if (!str || str === "None" || str === "N/A") return `<span class="text-muted">-</span>`;
                        if (str.length > 28) {
                            return `<div class="text-truncate cursor-pointer text-dark fw-medium" style="max-width: 140px;" title="${str.replace(/"/g, '&quot;')}">${str.substring(0, 26)}...</div>`;
                        }
                        return `<div style="max-width: 140px;" class="text-dark fw-medium">${str}</div>`;
                    }
                    
                    tbody.append(`
                        <tr data-report-id="${r.id}">
                            <td><strong>${r.representative}</strong></td>
                            <td class="text-nowrap">${r.date}</td>
                            <td>${r.client_name}</td>
                            <td><div class="text-truncate" style="max-width: 150px;">${r.summary || '-'}</div></td>
                            <td>${formatCell(r.sales_raw)}</td>
                            <td>${formatCell(r.collection_raw)}</td>
                            <td>${formatCell(r.competition_raw)}</td>
                            <td>${formatCell(r.product_raw)}</td>
                            <td>${formatCell(r.price_list_raw)}</td>
                            <td>${formatCell(r.our_services_raw)}</td>
                            <td>${formatCell(r.our_new_products_raw)}</td>
                            <td>${formatCell(r.most_sell_products_raw)}</td>
                            <td>${formatCell(r.pending_stock_raw)}</td>
                            <td class="text-nowrap">${(r.follow_up_date && r.follow_up_date !== 'None') ? r.follow_up_date : '-'}</td>
                            <td>${(r.voice_duration || 0).toFixed(1)}s</td>
                            <td><span class="${sentimentClass}">${sentValue}</span></td>
                        </tr>
                    `);
                });

                // Configure dynamic localization labels for DataTables search boxes
                const langCode = localStorage.getItem("pasas_lang") || "en";
                const dtLanguageConfig = langCode === "ta" ? {
                    search: "தேடுக:",
                    lengthMenu: "பக்கத்திற்கு _MENU_ பதிவுகளைக் காட்டு",
                    info: "மொத்தம் _TOTAL_ பதிவுகளில் _START_ முதல் _END_ வரையிலானவை",
                    paginate: {
                        first: "முதல்",
                        last: "கடைசி",
                        next: "அடுத்து",
                        previous: "முந்தைய"
                    },
                    emptyTable: "பதிவுகள் எதுவும் கிடைக்கவில்லை."
                } : {};

                analysisTable = $("#analysis-datatable").DataTable({
                    dom: "lrtip",
                    pageLength: 10,
                    ordering: true,
                    order: [[1, "desc"]],
                    info: true,
                    lengthChange: true,
                    paging: true,
                    language: dtLanguageConfig
                });

                $("#analysis-datatable tbody").off("click", "tr").on("click", "tr", function () {
                    const rId = $(this).data("report-id");
                    if (rId) {
                        openReportDetailModal(rId);
                    }
                });
            },
            error: function (xhr) {
                console.error("Failed to load reports table data", xhr);
            }
        });
    }

    // Reports exports handling (PDF, Excel, CSV)
    $("#btn-export-pdf, #btn-export-excel, #btn-export-csv").on("click", function (e) {
        e.preventDefault();
        const url = $(this).attr("href");
        const action = url.split("/").pop();
        let filename = "paccapro_sales_report.csv";
        if (action === "pdf") filename = "paccapro_sales_report.pdf";
        if (action === "excel") filename = "paccapro_sales_report.xlsx";

        $("#processing-overlay").removeClass("d-none");
        updateProcessingProgress(50, "Generating report file payload...");

        const xhr = new XMLHttpRequest();
        xhr.open("GET", url, true);
        xhr.setRequestHeader("Authorization", "Bearer " + authToken);
        xhr.responseType = "blob";

        xhr.onload = function () {
            $("#processing-overlay").addClass("d-none");
            if (xhr.status === 200) {
                const blob = xhr.response;
                const link = document.createElement("a");
                link.href = window.URL.createObjectURL(blob);
                link.download = filename;
                link.click();
            } else {
                alert("Failed to export files. Verify credentials and try again.");
            }
        };

        xhr.onerror = function () {
            $("#processing-overlay").addClass("d-none");
            alert("Connection error during report generation.");
        };

        xhr.send();
    });

    // Custom Filters logic
    $.fn.dataTable.ext.search.push(
        function (settings, data, dataIndex) {
            if (settings.nTable.id !== "analysis-datatable") return true;

            const fStart = $("#filter-start-date").val();
            const fEnd = $("#filter-end-date").val();
            const fRep = ($("#filter-rep").val() || "").trim().toLowerCase();
            const fSent = ($("#filter-sentiment").val() || "").trim().toLowerCase();

            const tRep = data[0].toLowerCase();
            const tDate = data[1];
            const tSent = (data[15] || "").toLowerCase();

            // 1. Sales Representative filter check
            if (fRep && !tRep.includes(fRep)) return false;

            // 2. Date Range filter check (inclusive lexicographical match)
            if (tDate) {
                if (fStart && tDate < fStart) return false;
                if (fEnd && tDate > fEnd) return false;
            }

            // 3. Sentiment filter check
            if (fSent && tSent !== fSent) return false;

            return true;
        }
    );

    $(".table-filter-input").on("change keyup", function () {
        if (analysisTable) analysisTable.draw();
    });

    $("#btn-reset-filters").on("click", function () {
        $(".table-filter-input").val("");
        if (analysisTable) analysisTable.draw();
    });

    // ==========================================
    // DETAIL POPUP MODAL
    // ==========================================

    function renderStarRating(stars) {
        stars = Math.max(1, Math.min(5, parseInt(stars) || 5));
        let html = "";
        for (let i = 1; i <= 5; i++) {
            if (i <= stars) html += '<i class="bi bi-star-fill text-warning me-1"></i>';
            else html += '<i class="bi bi-star text-secondary me-1"></i>';
        }
        return html;
    }

    function renderEmotionBadge(emotion) {
        const e = (emotion || "Positive").toString().toLowerCase();
        if (e.includes("pos") || e.includes("good")) {
            return '<span class="badge bg-success text-white px-2 py-1"><i class="bi bi-check-circle-fill me-1"></i> 🟢 Positive</span>';
        } else if (e.includes("neg") || e.includes("bad") || e.includes("not")) {
            return '<span class="badge bg-danger text-white px-2 py-1"><i class="bi bi-x-circle-fill me-1"></i> 🔴 Negative</span>';
        } else {
            return '<span class="badge bg-warning text-dark px-2 py-1"><i class="bi bi-dash-circle-fill me-1"></i> 🟡 Neutral</span>';
        }
    }

    function openReportDetailModal(reportId) {
        $.ajax({
            url: `${API_ROOT}/report/${reportId}`,
            type: "GET",
            success: function (r) {
                const overallRating = r.overall_rating || 5;
                const overallEmotion = r.overall_emotion || r.sentiment || "Positive";
                const tamilTranscript = r.tamil_transcript || "தமிழ் உரையாடல் பதிவு கிடைக்கவில்லை.";
                const englishTranscript = r.english_transcript || (r.conversations ? r.conversations.map(c => `${c.speaker}: ${c.text}`).join("\n") : "No English transcript available.");

                let html = `
                    <!-- Conversation Analysis Header Card -->
                    <div class="p-3 bg-light rounded border border-secondary-subtle mb-4">
                        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3 pb-2 border-bottom border-secondary-subtle">
                            <div>
                                <h5 class="text-dark fw-bold mb-0">Conversation Analysis</h5>
                                <span class="text-muted tiny">Sales Rep & Dealer Interaction Metrics</span>
                            </div>
                            <div class="d-flex align-items-center gap-3">
                                <div>
                                    <span class="text-muted tiny text-uppercase d-block">Overall Rating</span>
                                    <span class="fs-5">${renderStarRating(overallRating)}</span>
                                </div>
                                <div>
                                    <span class="text-muted tiny text-uppercase d-block">Overall Emotion</span>
                                    ${renderEmotionBadge(overallEmotion)}
                                </div>
                            </div>
                        </div>

                        <div class="row g-3">
                            <div class="col-md-4">
                                <label class="text-muted tiny text-uppercase">Sales Representative</label>
                                <div class="fw-bold fs-6 text-dark">${r.representative}</div>
                            </div>
                            <div class="col-md-4">
                                <label class="text-muted tiny text-uppercase">Dealer / Client Name</label>
                                <div class="fw-bold fs-6 text-dark">${r.client_name}</div>
                            </div>
                            <div class="col-md-4">
                                <label class="text-muted tiny text-uppercase">Meeting Date</label>
                                <div class="fw-bold fs-6 text-dark">${r.date}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Overall Summary -->
                    <div class="mb-4">
                        <h6 class="text-dark fw-bold mb-2">Overall Summary</h6>
                        <div class="p-3 bg-light rounded border border-secondary-subtle lh-sm text-dark">${r.summary || 'No summary generated.'}</div>
                    </div>

                    <!-- Dual Transcripts Section -->
                    <div class="row g-3 mb-4">
                        <!-- Tamil Transcript -->
                        <div class="col-md-6">
                            <h6 class="text-dark fw-bold mb-2"><i class="bi bi-translate text-primary me-1"></i> Tamil Transcript</h6>
                            <div class="p-3 bg-light rounded border border-primary-subtle text-dark font-monospace" style="max-height: 250px; overflow-y: auto; white-space: pre-wrap; font-size: 0.88rem;">${tamilTranscript}</div>
                        </div>
                        <!-- English Transcript -->
                        <div class="col-md-6">
                            <h6 class="text-dark fw-bold mb-2"><i class="bi bi-chat-left-text text-success me-1"></i> English Transcript</h6>
                            <div class="p-3 bg-light rounded border border-success-subtle text-dark font-monospace" style="max-height: 250px; overflow-y: auto; white-space: pre-wrap; font-size: 0.88rem;">${englishTranscript}</div>
                        </div>
                    </div>

                    <!-- 10 Topic Performance Table -->
                    <h6 class="text-dark fw-bold mb-2">10 Topic Performance & Emotion Breakdown</h6>
                    <div class="table-responsive mb-4">
                        <table class="table custom-table text-dark bg-light rounded border border-secondary-subtle overflow-hidden">
                            <thead>
                                <tr class="table-dark">
                                    <th>Topic</th>
                                    <th>Rating</th>
                                    <th>Emotion</th>
                                    <th>Extracted Detail / Summary</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="fw-bold text-dark">1. Sales</td>
                                    <td>${renderStarRating(5)}</td>
                                    <td>${renderEmotionBadge("Positive")}</td>
                                    <td><strong>${r.sales_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">2. Collection</td>
                                    <td>${renderStarRating(4)}</td>
                                    <td>${renderEmotionBadge("Positive")}</td>
                                    <td><strong>${r.collection_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">3. Competition</td>
                                    <td>${renderStarRating(3)}</td>
                                    <td>${renderEmotionBadge("Negative")}</td>
                                    <td><strong>${r.competition_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">4. Product</td>
                                    <td>${renderStarRating(5)}</td>
                                    <td>${renderEmotionBadge("Positive")}</td>
                                    <td><strong>${r.product_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">5. Price List</td>
                                    <td>${renderStarRating(3)}</td>
                                    <td>${renderEmotionBadge("Neutral")}</td>
                                    <td><strong>${r.price_list_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">6. Our Services</td>
                                    <td>${renderStarRating(4)}</td>
                                    <td>${renderEmotionBadge("Positive")}</td>
                                    <td><strong>${r.our_services_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">7. Our New Products</td>
                                    <td>${renderStarRating(4)}</td>
                                    <td>${renderEmotionBadge("Positive")}</td>
                                    <td><strong>${r.our_new_products_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">8. Most Sell Products</td>
                                    <td>${renderStarRating(5)}</td>
                                    <td>${renderEmotionBadge("Positive")}</td>
                                    <td><strong>${r.most_sell_products_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">9. Pending Stock</td>
                                    <td>${renderStarRating(3)}</td>
                                    <td>${renderEmotionBadge("Negative")}</td>
                                    <td><strong>${r.pending_stock_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="fw-bold text-dark">10. Follow-Up Date</td>
                                    <td>${renderStarRating(5)}</td>
                                    <td>${renderEmotionBadge("Positive")}</td>
                                    <td><strong>${r.follow_up_date || 'Scheduled'}</strong></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="mt-3 text-muted tiny">Report registered: ${new Date(r.created_at).toLocaleString()}</div>
                `;

                // Render strong text headers
                html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

                $("#modal-report-content").html(html);
                
                const myModal = new bootstrap.Modal(document.getElementById('reportDetailModal'));
                myModal.show();
            },
            error: function (xhr) {
                alert("Failed to retrieve report data details.");
            }
        });
    }

    function formatTime(secs) {
        if (secs === null || secs === undefined) return "00:00";
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    // ==========================================
    // VIEW 3: SYNC & ANALYZE WORKFLOW
    // ==========================================

    function loadSyncDashboard() {
        $.ajax({
            url: `${API_ROOT}/sync/status`,
            type: "GET",
            beforeSend: function(xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function (res) {
                $("#sync-val-last-time").text(res.last_sync_time);
                $("#sync-val-pending").text(res.pending_recordings);
                $("#sync-val-downloaded").text(res.total_downloaded);
                $("#sync-val-analyzed").text(res.total_analyzed);
                $("#sync-text-storage").text(res.storage_used);
                
                // Update Connection/Server/AI badges
                $("#sync-badge-conn").text(translations["sync_status_connected"] || "Connected");
                $("#sync-badge-srv").text(translations["sync_status_online"] || "Online");
                $("#sync-badge-ai").text(translations["sync_status_ready"] || "Ready");
            },
            error: function (xhr) {
                console.error("Failed to load sync status metrics", xhr);
            }
        });
    }

    function loadSyncHistory() {
        $.ajax({
            url: `${API_ROOT}/sync/history`,
            type: "GET",
            beforeSend: function(xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function (history) {
                const tbody = $("#sync-history-tbody");
                tbody.empty();
                if (history.length === 0) {
                    tbody.append(`<tr><td colspan="5" class="text-center text-muted py-3">No sync history logs available.</td></tr>`);
                    return;
                }
                history.forEach(item => {
                    tbody.append(`
                        <tr>
                            <td>${item.date}</td>
                            <td><strong>${item.downloaded_files}</strong></td>
                            <td><strong>${item.analyzed_files}</strong></td>
                            <td>${item.duration}</td>
                            <td><span class="badge ${item.status === 'Success' ? 'bg-success' : 'bg-danger'}">${item.status}</span></td>
                        </tr>
                    `);
                });
            },
            error: function (xhr) {
                console.error("Failed to load sync history logs", xhr);
            }
        });
    }

    $("#btn-trigger-sync").on("click", function () {
        const btn = $(this);
        const icon = $("#icon-sync-spin");
        const consoleEl = $("#sync-logs-console");
        
        btn.prop("disabled", true);
        icon.addClass("fa-spin");

        consoleEl.empty();
        
        function logMsg(msg, isHeader = false) {
            const timeStr = new Date().toLocaleTimeString();
            const classAttr = isHeader ? 'class="text-info fw-bold"' : '';
            consoleEl.append(`<div ${classAttr}>[${timeStr}] ${msg}</div>`);
            consoleEl.scrollTop(consoleEl[0].scrollHeight);
        }

        logMsg("Step 1/12: Connecting to remote cloud server...");
        
        setTimeout(() => {
            logMsg("Step 2/12: Verification successful. Querying pending recordings registry...");
            
            $.ajax({
                url: `${API_ROOT}/sync/run`,
                type: "POST",
                beforeSend: function(xhr) {
                    xhr.setRequestHeader("Authorization", "Bearer " + authToken);
                },
                success: function (res) {
                    if (res.status === "synchronized") {
                        logMsg("Step 3/12: Display registry check results.");
                        logMsg("No new recordings available. Everything is already synchronized.", true);
                        logMsg("Synchronization Completed Successfully", true);
                        
                        btn.prop("disabled", false);
                        icon.removeClass("fa-spin");
                        
                        loadSyncDashboard();
                        loadSyncHistory();
                        return;
                    }

                    const numRecs = res.downloaded;
                    logMsg(`Step 3/12: Display - Found ${numRecs} new recordings.`);
                    logMsg(`Step 4/12: Downloading all ${numRecs} pending records...`);
                    
                    setTimeout(() => {
                        logMsg("Step 5/12: Download successful. Storing recordings locally in uploads/voice/...");
                        
                        setTimeout(() => {
                            logMsg("Step 6/12: Running local Speech-to-Text Whisper transcription...");
                            
                            setTimeout(() => {
                                logMsg("Step 7/12: Running bilingual translation checks...");
                                
                                setTimeout(() => {
                                    logMsg("Step 8/12: Running local Ollama Llama3 AI Analysis and sentiment tagging...");
                                    
                                    setTimeout(() => {
                                        logMsg("Step 9/12: Generating pipeline summaries and Excel/PDF reports...");
                                        
                                        setTimeout(() => {
                                            logMsg("Step 10/12: Updating database indices and refreshing Dashboard cards...");
                                            
                                            setTimeout(() => {
                                                logMsg("Step 11/12: Marking downloaded records as synchronized on server registry...");
                                                
                                                setTimeout(() => {
                                                    logMsg("Step 12/12: Synchronization Completed Successfully", true);
                                                    
                                                    btn.prop("disabled", false);
                                                    icon.removeClass("fa-spin");
                                                    
                                                    // Refresh all interface elements
                                                    loadSyncDashboard();
                                                    loadSyncHistory();
                                                    loadDashboardData();
                                                }, 500);
                                            }, 500);
                                        }, 500);
                                    }, 500);
                                }, 500);
                            }, 500);
                        }, 500);
                    }, 500);
                },
                error: function (xhr) {
                    logMsg("ERROR: Unable to connect to server.", true);
                    logMsg("Please check your internet connection and backend sync service URL config.", true);
                    
                    btn.prop("disabled", false);
                    icon.removeClass("fa-spin");
                    
                    loadSyncDashboard();
                    loadSyncHistory();
                }
            });
        }, 1000);
    });

    function updateProcessingProgress(percentage, text) {
        $("#processing-progress").css("width", `${percentage}%`);
        $("#processing-status").text(text);
    }

    // ==========================================
    // VIEW 4: STREAMING AI ASSISTANT CHAT
    // ==========================================

    function loadChatHistory() {
        $.ajax({
            url: `${API_ROOT}/chat/history`,
            type: "GET",
            success: function (history) {
                const msgArea = $("#chat-messages");
                
                const welcomeText = translations["chat_welcome"] || "Hello! I am your PaccaPro AI Assistant. I operate offline and have direct access to your local SQLite sales database.";
                const welcomeSubText = translations["chat_welcome_sub"] || "Ask me things like:";

                // Reset viewport
                msgArea.html(`
                    <div class="assistant-bubble d-flex gap-3 mb-4">
                        <div class="assistant-avatar">AI</div>
                        <div class="bubble-content">
                            <p class="mb-0">${welcomeText}</p>
                            <p class="mb-0 mt-2">${welcomeSubText}</p>
                            <ul class="mb-0 mt-1 pl-3">
                                <li>"Show today's reports"</li>
                                <li>"List today's collections"</li>
                                <li>"Show Balaji's clients today"</li>
                                <li>"Show all complaints"</li>
                                <li>"Compare monthly performance"</li>
                            </ul>
                        </div>
                    </div>
                `);

                history.forEach(h => {
                    msgArea.append(`
                        <div class="user-bubble">
                            <p class="mb-0">${h.message}</p>
                        </div>
                    `);

                    const formattedHtml = parseMarkdownToHtml(h.response);
                    msgArea.append(`
                        <div class="assistant-bubble d-flex gap-3 mb-4">
                            <div class="assistant-avatar">AI</div>
                            <div class="bubble-content">
                                <div>${formattedHtml}</div>
                            </div>
                        </div>
                    `);
                });

                msgArea.scrollTop(msgArea[0].scrollHeight);
            }
        });
    }

    $("#chat-form").on("submit", function (e) {
        e.preventDefault();
        const userMsg = $("#chat-input").val().trim();
        if (!userMsg) return;

        submitChatMessageStream(userMsg);
    });

    $(".suggestion-item").on("click", function () {
        const query = $(this).data("prompt");
        submitChatMessageStream(query);
    });

    function submitChatMessageStream(messageText) {
        const msgArea = $("#chat-messages");
        
        msgArea.append(`
            <div class="user-bubble">
                <p class="mb-0">${messageText}</p>
            </div>
        `);
        msgArea.scrollTop(msgArea[0].scrollHeight);
        $("#chat-input").val("");

        const typingId = `typing-${Date.now()}`;
        msgArea.append(`
            <div class="assistant-bubble d-flex gap-3 mb-4" id="${typingId}">
                <div class="assistant-avatar">AI</div>
                <div class="bubble-content">
                    <div class="typing-dots">
                        <span></span> <span></span> <span></span>
                    </div>
                </div>
            </div>
        `);
        msgArea.scrollTop(msgArea[0].scrollHeight);

        fetch(`${API_ROOT}/chat/stream`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + authToken
            },
            body: JSON.stringify({ message: messageText })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Server returned API error");
            }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            $(`#${typingId}`).remove();
            
            const streamId = `stream-bubble-${Date.now()}`;
            msgArea.append(`
                <div class="assistant-bubble d-flex gap-3 mb-4" id="${streamId}">
                    <div class="assistant-avatar">AI</div>
                    <div class="bubble-content">
                        <div class="stream-text"></div>
                    </div>
                </div>
            `);
            msgArea.scrollTop(msgArea[0].scrollHeight);
            
            const streamContainer = $(`#${streamId} .stream-text`);
            let cumulativeText = "";

            function readStreamChunk() {
                return reader.read().then(({ done, value }) => {
                    if (done) {
                        const finalHtml = parseMarkdownToHtml(cumulativeText);
                        streamContainer.html(finalHtml);
                        msgArea.scrollTop(msgArea[0].scrollHeight);
                        return;
                    }
                    
                    const chunk = decoder.decode(value, { stream: true });
                    cumulativeText += chunk;
                    
                    const tempText = cumulativeText
                        .replace(/&/g, "&amp;")
                        .replace(/</g, "&lt;")
                        .replace(/>/g, "&gt;")
                        .replace(/\n/g, "<br>")
                        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
                        
                    streamContainer.html(tempText);
                    msgArea.scrollTop(msgArea[0].scrollHeight);
                    
                    return readStreamChunk();
                });
            }
            
            return readStreamChunk();
        })
        .catch(err => {
            $(`#${typingId}`).remove();
            msgArea.append(`
                <div class="assistant-bubble d-flex gap-3 mb-4">
                    <div class="assistant-avatar">AI</div>
                    <div class="bubble-content">
                        <span class="text-danger small">Streaming connection timed out.</span>
                    </div>
                </div>
            `);
            msgArea.scrollTop(msgArea[0].scrollHeight);
        });
    }

    function parseMarkdownToHtml(text) {
        let escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        escaped = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        escaped = escaped.replace(/`(.*?)`/g, "<code>$1</code>");

        const lines = escaped.split("\n");
        let htmlLines = [];
        let inTable = false;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            if (line.startsWith("|") && line.endsWith("|")) {
                const cells = line.split("|").map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
                
                if (!inTable) {
                    inTable = true;
                    htmlLines.push('<div class="table-responsive"><table class="table custom-table text-dark mb-0"><thead>');
                    htmlLines.push("<tr>" + cells.map(c => `<th>${c}</th>`).join("") + "</tr>");
                    htmlLines.push("</thead><tbody>");
                    if (i + 1 < lines.length && lines[i+1].includes("---")) {
                        i++;
                    }
                } else {
                    htmlLines.push("<tr>" + cells.map(c => `<td>${c}</td>`).join("") + "</tr>");
                }
            } else {
                if (inTable) {
                    inTable = false;
                    htmlLines.push("</tbody></table></div>");
                }
                htmlLines.push(line ? `<p class="mb-1 text-dark">${line}</p>` : "");
            }
        }
        
        if (inTable) {
            htmlLines.push("</tbody></table></div>");
        }

        return htmlLines.join("");
    }

    // ==========================================
    // POSTER ANALYSIS LOGIC IMPLEMENTATION
    // ==========================================

    let selectedPosterFile = null;
    let currentRotation = 0;
    let currentScale = 1.0;
    let posterTable = null;
    let chartPosterCats = null;
    let chartPosterLangs = null;

    // Trigger initialization of dropzone events
    initPosterDropzone();

    function initPosterDropzone() {
        const dropzone = $("#poster-dropzone");
        const fileInput = $("#poster-file-input");

        dropzone.on("click", function () {
            fileInput.click();
        });

        dropzone.on("dragover", function (e) {
            e.preventDefault();
            dropzone.addClass("border-primary").css("background-color", "rgba(37, 99, 235, 0.05)");
        });

        dropzone.on("dragleave drop", function (e) {
            e.preventDefault();
            dropzone.removeClass("border-primary").css("background-color", "");
        });

        dropzone.on("drop", function (e) {
            const files = e.originalEvent.dataTransfer.files;
            if (files.length > 0) {
                handlePosterFileSelection(files[0]);
            }
        });

        fileInput.on("change", function () {
            if (this.files.length > 0) {
                handlePosterFileSelection(this.files[0]);
            }
        });

        // Rotate control
        $("#btn-preview-rotate").on("click", function () {
            currentRotation = (currentRotation + 90) % 360;
            applyPreviewTransforms();
        });

        // Zoom controls
        $("#btn-preview-zoom-in").on("click", function () {
            currentScale = Math.min(2.5, currentScale + 0.15);
            applyPreviewTransforms();
        });

        $("#btn-preview-zoom-out").on("click", function () {
            currentScale = Math.max(0.5, currentScale - 0.15);
            applyPreviewTransforms();
        });

        // Fullscreen preview
        $("#btn-preview-fullscreen").on("click", function () {
            const src = $("#poster-preview-img").attr("src");
            if (src) {
                window.open(src, "_blank");
            }
        });

        // Clear button
        $("#btn-clear-poster").on("click", function () {
            clearPosterUpload();
        });

        // Analyze button
        $("#btn-analyze-poster").on("click", function () {
            triggerPosterAnalysis();
        });
    }

    function applyPreviewTransforms() {
        $("#poster-preview-img").css("transform", `rotate(${currentRotation}deg) scale(${currentScale})`);
    }

    function handlePosterFileSelection(file) {
        // Validation: Size < 50MB
        const sizeMb = file.size / (1024 * 1024);
        if (sizeMb > 50) {
            alert("File is too large! Maximum limit is 50MB.");
            return;
        }

        // Validation: Format Check
        const ext = file.name.split('.').pop().toLowerCase();
        if (!["png", "jpg", "jpeg", "webp"].includes(ext)) {
            alert("Unsupported format. Only PNG, JPG, JPEG, and WEBP images allowed.");
            return;
        }

        selectedPosterFile = file;

        // Set name and size
        $("#poster-filename").text(file.name);
        $("#poster-filesize").text(`${sizeMb.toFixed(2)} MB`);
        
        // Show progress and hide placeholder dropzone text
        $("#poster-upload-progress-card").removeClass("d-none");
        $("#poster-progress-bar").css("width", "0%");
        $("#poster-percent").text("0%");

        // Create local reader for preview
        const reader = new FileReader();
        reader.onload = function (e) {
            const img = new Image();
            img.onload = function () {
                $("#poster-resolution").text(`Resolution: ${this.width} x ${this.height}`);
                $("#poster-metadata-overlay").text(`Resolution: ${this.width} x ${this.height} | Size: ${sizeMb.toFixed(2)} MB`);
            };
            img.src = e.target.result;
            
            $("#poster-preview-img").attr("src", e.target.result);
            $("#poster-preview-wrapper").removeClass("d-none");
        };
        reader.readAsDataURL(file);

        // Reset transforms
        currentRotation = 0;
        currentScale = 1.0;
        applyPreviewTransforms();

        // Enable buttons
        $("#btn-analyze-poster").prop("disabled", false);
        $("#btn-clear-poster").prop("disabled", false);
    }

    function clearPosterUpload() {
        selectedPosterFile = null;
        $("#poster-file-input").val("");
        $("#poster-upload-progress-card").addClass("d-none");
        $("#poster-preview-wrapper").addClass("d-none");
        $("#poster-preview-img").attr("src", "");
        $("#btn-analyze-poster").prop("disabled", true);
        $("#btn-clear-poster").prop("disabled", true);
    }

    async function triggerPosterAnalysis() {
        if (!selectedPosterFile) return;

        // Check Ollama and vision model status first
        try {
            const statusRes = await $.ajax({
                url: `${API_ROOT}/api/ollama/status`,
                type: "GET",
                beforeSend: function (xhr) {
                    xhr.setRequestHeader("Authorization", "Bearer " + authToken);
                }
            });

            if (!statusRes.available) {
                alert("Unable to connect to Ollama.\nMake sure Ollama is running on localhost:11434.");
                return;
            }

            if (!statusRes.vision) {
                alert("Gemma 3 vision model is not installed.\n\nPlease run:\nollama pull gemma3:4b");
                return;
            }
        } catch (e) {
            alert("Unable to connect to Ollama.\nMake sure Ollama is running on localhost:11434.");
            return;
        }

        const formData = new FormData();
        formData.append("file", selectedPosterFile);

        // Show global processing overlay
        $("#processing-overlay").removeClass("d-none");
        $("#processing-title").text("OCR Engine Ingestion Running");
        $("#processing-status").text("Extracting marketing text and checking duplicate hash signatures...");
        $("#processing-progress").css("width", "10%");

        // 1. Upload Poster
        $.ajax({
            url: `${API_ROOT}/poster/upload`,
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            beforeSend: function (xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: async function (uploadRes) {
                $("#processing-status").text("Checking duplicate...");
                $("#processing-progress").css("width", "20%");

                if (uploadRes.duplicate) {
                    console.log("Duplicate poster detected — re-analyzing image with Ollama.");
                }

                // 2. Trigger streaming analysis endpoint using Fetch
                const analyzeData = new FormData();
                analyzeData.append("filename", uploadRes.filename);
                analyzeData.append("image_hash", uploadRes.image_hash);

                try {
                    const response = await fetch(`${API_ROOT}/poster/analyze`, {
                        method: "POST",
                        headers: {
                            "Authorization": "Bearer " + authToken
                        },
                        body: analyzeData
                    });

                    if (!response.ok) {
                        const errText = await response.text();
                        throw new Error(errText || "Analysis trigger failed");
                    }

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = "";

                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split("\n");
                        
                        // Keep the last partial line in the buffer
                        buffer = lines.pop();

                        for (const line of lines) {
                            const trimmed = line.trim();
                            if (!trimmed) continue;

                            let eventData = trimmed;
                            if (trimmed.startsWith("data: ")) {
                                eventData = trimmed.replace("data: ", "");
                            }

                            try {
                                const payload = JSON.parse(eventData);
                                if (!payload) continue;

                                if (payload.step === -1) {
                                    // Error reported from backend
                                    throw new Error(payload.message);
                                }

                                // Update overlay progress
                                $("#processing-status").text(payload.message);
                                const progressPct = Math.min(100, payload.step * 9);
                                $("#processing-progress").css("width", `${progressPct}%`);

                                if (payload.step === 5 || payload.step === 11) {
                                    // Complete
                                    $("#processing-overlay").addClass("d-none");
                                    console.log("Poster Analysis Complete!");
                                    loadPosterDetails(payload.id);
                                    clearPosterUpload();
                                    loadPosterDashboard();
                                }
                            } catch (e) {
                                console.error("Error parsing stream chunk", e);
                                if (e.message && e.message.indexOf("JSON") === -1) {
                                    throw e;
                                }
                            }
                        }
                    }
                } catch (err) {
                    $("#processing-overlay").addClass("d-none");
                    alert("Poster analysis failed:\n" + err.message);
                }
            },
            error: function (xhr) {
                $("#processing-overlay").addClass("d-none");
                alert("Poster upload failed: " + (xhr.responseJSON?.detail || "Please upload a valid JPG, JPEG, PNG or WEBP image."));
            }
        });
    }

    function loadPosterDetails(posterId) {
        $.ajax({
            url: `${API_ROOT}/poster/${posterId}`,
            type: "GET",
            beforeSend: function (xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function (res) {
                // 1. Extracted OCR Text
                $("#res-ocr-text").text(res.ocr_text || "No OCR text extracted.");

                // Copy OCR button click handler
                $("#btn-copy-ocr").off("click").on("click", function () {
                    const text = $("#res-ocr-text").text();
                    if (!text || text === "No OCR text extracted.") {
                        alert("No OCR text to copy.");
                        return;
                    }
                    navigator.clipboard.writeText(text).then(() => {
                        const origHtml = $(this).html();
                        $(this).html('<i class="bi bi-check me-1"></i>Copied!');
                        setTimeout(() => $(this).html(origHtml), 2000);
                    }).catch(() => {
                        alert("Failed to copy text to clipboard.");
                    });
                });

                // 2. Important Information Grid
                const grid = $("#res-important-info-grid");
                grid.empty();

                let info = res.important_information || {};
                if (typeof info === 'string') {
                    try { info = JSON.parse(info); } catch (e) { info = {}; }
                }

                function formatVal(val) {
                    if (val === null || val === undefined || val === "" || val === "None" || val === "null" || (Array.isArray(val) && val.length === 0)) {
                        return '<span class="text-muted">None</span>';
                    }
                    if (Array.isArray(val)) {
                        return val.join(", ");
                    }
                    return String(val);
                }

                const fieldsToDisplay = [
                    { label: "Emails", val: info.emails },
                    { label: "Phones", val: info.phones },
                    { label: "Websites", val: info.websites },
                    { label: "Venue", val: info.venue },
                    { label: "Date / Time", val: info.date_time || info.date },
                    { label: "Coupon Code", val: info.coupon_code },
                    { label: "Price", val: info.price || (res.price !== "None" ? res.price : null) },
                    { label: "Brand", val: info.brand || res.brand },
                    { label: "Product / Service", val: info.product_service || res.product },
                    { label: "Offer", val: info.offer || (res.offer !== "None" ? res.offer : null) },
                    { label: "Address", val: info.address },
                    { label: "Contact Person", val: info.contact_person },
                    { label: "Social Media", val: info.social_media },
                    { label: "Call To Action", val: info.call_to_action || res.call_to_action }
                ];

                fieldsToDisplay.forEach(item => {
                    grid.append(`
                        <div class="col-md-6 mb-2">
                            <span class="text-muted tiny text-uppercase d-block fw-semibold">${item.label}</span>
                            <div class="text-white small fw-bold">${formatVal(item.val)}</div>
                        </div>
                    `);
                });

                // 3. Overall Summary
                $("#res-overall-summary").text(res.summary || res.detailed_summary || "No summary available.");

                // 4. AI Marketing Suggestions
                const suggUl = $("#res-suggestions-list");
                suggUl.empty();
                
                const ms = res.marketing_suggestions || [];
                const ims = res.improvement_suggestions || [];
                
                if (ms.length === 0 && ims.length === 0) {
                    suggUl.append(`<li>No major suggestions. Visual layout meets guidelines.</li>`);
                } else {
                    ms.forEach(s => {
                        suggUl.append(`<li><strong>Marketing:</strong> ${s}</li>`);
                    });
                    ims.forEach(s => {
                        suggUl.append(`<li><strong>Design:</strong> ${s}</li>`);
                    });
                }

                // Show results panel
                $("#poster-results-placeholder").addClass("d-none");
                $("#poster-results-content").removeClass("d-none");
            },
            error: function () {
                console.error("Failed to load details for poster: " + posterId);
            }
        });
    }

    function loadPosterDashboard() {
        $.ajax({
            url: `${API_ROOT}/poster/history`,
            type: "GET",
            beforeSend: function (xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function (history) {
                const totalCount = history.length;
                
                // Calculate today's uploads count
                const todayStr = new Date().toISOString().split('T')[0];
                const todayCount = history.filter(item => item.created_at.startsWith(todayStr)).length;

                // Unique Categories & Languages counts
                const categories = [...new Set(history.map(h => h.poster_category))];
                const languages = [...new Set(history.map(h => h.language))];
                
                // Averages Confidences
                let ocrTotal = 0, aiTotal = 0;
                history.forEach(h => {
                    ocrTotal += h.ocr_confidence || 0;
                    aiTotal += h.ai_confidence || 0;
                });
                const avgOcr = totalCount > 0 ? (ocrTotal / totalCount) * 100 : 0;
                const avgAi = totalCount > 0 ? (aiTotal / totalCount) * 100 : 0;

                // Set stat values
                $("#card-total-posters").text(totalCount);
                $("#card-today-posters").text(todayCount);
                $("#card-categories-count").text(categories.length);
                $("#card-languages-count").text(languages.length);
                $("#card-avg-ocr").text(`${avgOcr.toFixed(0)}%`);
                $("#card-avg-ai").text(`${avgAi.toFixed(0)}%`);

                // Categories distribution chart data aggregation
                const catCounts = {};
                history.forEach(item => {
                    catCounts[item.poster_category] = (catCounts[item.poster_category] || 0) + 1;
                });

                // Languages distribution data aggregation
                const langCounts = {};
                history.forEach(item => {
                    langCounts[item.language] = (langCounts[item.language] || 0) + 1;
                });

                // Re-draw categories doughnut/pie chart
                if (chartPosterCats) chartPosterCats.destroy();
                const catsCtx = document.getElementById("chart-poster-categories");
                if (catsCtx) {
                    chartPosterCats = new Chart(catsCtx, {
                        type: "doughnut",
                        data: {
                            labels: Object.keys(catCounts),
                            datasets: [{
                                data: Object.values(catCounts),
                                backgroundColor: ["#2563eb", "#10b981", "#8b5cf6", "#ea580c", "#06b6d4", "#ef4444"],
                                borderWidth: 1,
                                borderColor: "#ffffff"
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: "right",
                                    labels: { color: "#94a3b8" }
                                }
                            }
                        }
                    });
                }

                // Re-draw languages bar chart
                if (chartPosterLangs) chartPosterLangs.destroy();
                const langsCtx = document.getElementById("chart-poster-languages");
                if (langsCtx) {
                    chartPosterLangs = new Chart(langsCtx, {
                        type: "bar",
                        data: {
                            labels: Object.keys(langCounts),
                            datasets: [{
                                label: "Posters Count",
                                data: Object.values(langCounts),
                                backgroundColor: "#10b981",
                                borderRadius: 4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                x: { ticks: { color: "#94a3b8" } },
                                y: { ticks: { color: "#94a3b8" } }
                            }
                        }
                    });
                }

                // Render DataTable
                renderPosterHistoryTable(history);
            },
            error: function () {
                console.error("Failed to load poster history stats data.");
            }
        });
    }

    function renderPosterHistoryTable(data) {
        if (posterTable) {
            posterTable.destroy();
        }

        const tbody = $("#poster-history-tbody");
        tbody.empty();

        data.forEach(item => {
            tbody.append(`
                <tr data-id="${item.id}">
                    <td class="text-center"><img src="${item.image_url}" width="36" height="36" class="img-thumbnail rounded" style="object-fit: cover; cursor: pointer;" onclick="window.open('${item.image_url}', '_blank')"></td>
                    <td><strong>${item.poster_title || "Untitled"}</strong></td>
                    <td><span class="badge bg-secondary">${item.poster_category || "Promotional Poster"}</span></td>
                    <td>${item.language || "English"}</td>
                    <td>${item.uploaded_by || "User"}</td>
                    <td>${item.created_at}</td>
                    <td class="text-truncate" style="max-width: 180px;" title="${item.summary || ''}">${item.summary || "N/A"}</td>
                    <td><span class="badge bg-success">${item.status || "Analyzed"}</span></td>
                    <td>
                        <div class="dropdown">
                            <button class="btn btn-outline-secondary btn-xs dropdown-toggle" type="button" data-bs-toggle="dropdown">Actions</button>
                            <ul class="dropdown-menu dropdown-menu-dark">
                                <li><a class="dropdown-item btn-action-view" href="#" onclick="openPosterDetail(${item.id})"><i class="bi bi-eye me-1"></i>View Analysis</a></li>
                                <li><a class="dropdown-item" href="#" onclick="viewOcrTextModal(${item.id})"><i class="bi bi-file-text me-1"></i>View OCR Text</a></li>
                                <li><a class="dropdown-item" href="#" onclick="copyOcrTextById(${item.id})"><i class="bi bi-clipboard me-1"></i>Copy OCR</a></li>
                                <li><a class="dropdown-item text-warning" href="#" onclick="reanalyzePoster(${item.id})"><i class="bi bi-arrow-repeat me-1"></i>Re-analyze</a></li>
                                <li><a class="dropdown-item text-danger" href="#" onclick="deletePoster(${item.id})"><i class="bi bi-trash me-1"></i>Delete</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item" href="${API_ROOT}/poster/${item.id}/export/pdf" target="_blank"><i class="bi bi-file-earmark-pdf me-1"></i>Download PDF</a></li>
                                <li><a class="dropdown-item" href="${API_ROOT}/poster/${item.id}/export/json" target="_blank"><i class="bi bi-file-earmark-code me-1"></i>Export JSON</a></li>
                            </ul>
                        </div>
                    </td>
                </tr>
            `);
        });

        // Initialize DataTable
        posterTable = $("#poster-history-table").DataTable({
            pageLength: 5,
            lengthMenu: [5, 10, 20],
            ordering: true,
            destroy: true,
            searching: true,
            columnDefs: [
                { orderable: false, targets: [0, 8] }
            ]
        });
    }

    window.copyOcrTextById = function(id) {
        $.ajax({
            url: `${API_ROOT}/poster/${id}`,
            type: "GET",
            beforeSend: function (xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function (res) {
                if (res.ocr_text) {
                    navigator.clipboard.writeText(res.ocr_text).then(() => {
                        alert("OCR text copied to clipboard!");
                    }).catch(() => {
                        alert("Failed to copy OCR text.");
                    });
                } else {
                    alert("No OCR text available for this poster.");
                }
            }
        });
    };

    window.viewOcrTextModal = function(id) {
        window.openPosterDetail(id);
        setTimeout(() => {
            const ocrTab = document.getElementById("ocr-tab");
            if (ocrTab) {
                const bsTab = new bootstrap.Tab(ocrTab);
                bsTab.show();
            }
        }, 300);
    };

    // Modal Operations global functions
    window.openPosterDetail = function (id) {
        $.ajax({
            url: `${API_ROOT}/poster/${id}`,
            type: "GET",
            beforeSend: function (xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function (res) {
                $("#detail-poster-img").attr("src", res.image_url);
                $("#detail-poster-meta").text(`Filename: ${res.filename} | Uploaded By: ${res.uploaded_by} | Date: ${res.created_at}`);
                
                $("#detail-poster-title").val(res.poster_title);
                $("#detail-poster-category").val(res.poster_category);
                $("#detail-poster-language").val(res.language);
                $("#detail-poster-heading").val(res.main_heading);
                $("#detail-poster-subheading").val(res.sub_heading);

                $("#detail-summary-p").text(res.detailed_summary || res.summary);
                
                const hlUl = $("#detail-highlights-ul");
                hlUl.empty();
                (res.highlights || []).forEach(hl => {
                    hlUl.append(`<li>${hl}</li>`);
                });

                const contactsUl = $("#detail-contacts-ul");
                contactsUl.empty();
                const info = res.important_information || {};
                contactsUl.append(`<li><strong>Emails:</strong> ${info.emails?.join(", ") || "None"}</li>`);
                contactsUl.append(`<li><strong>Phones:</strong> ${info.phones?.join(", ") || "None"}</li>`);
                contactsUl.append(`<li><strong>Websites:</strong> ${info.urls?.join(", ") || "None"}</li>`);
                contactsUl.append(`<li><strong>Venue:</strong> ${info.venue || "N/A"}</li>`);
                contactsUl.append(`<li><strong>Date / Time:</strong> ${info.date || "N/A"} at ${info.time || "N/A"}</li>`);
                contactsUl.append(`<li><strong>Coupon Code:</strong> ${info.coupon_code || "None"} (Discount: ${info.discount || "None"})</li>`);
                contactsUl.append(`<li><strong>Price:</strong> ${info.price || "N/A"}</li>`);

                $("#detail-tab-ocr").text(res.ocr_text);

                // Bind Save Changes click handler
                $("#btn-detail-save").off("click").on("click", function () {
                    const payload = {
                        poster_title: $("#detail-poster-title").val(),
                        poster_category: $("#detail-poster-category").val(),
                        main_heading: $("#detail-poster-heading").val(),
                        sub_heading: $("#detail-poster-subheading").val()
                    };

                    $.ajax({
                        url: `${API_ROOT}/poster/${id}`,
                        type: "PUT",
                        contentType: "application/json",
                        data: JSON.stringify(payload),
                        beforeSend: function (xhr) {
                            xhr.setRequestHeader("Authorization", "Bearer " + authToken);
                        },
                        success: function () {
                            console.log("Poster updated successfully.");
                            bootstrap.Modal.getInstance(document.getElementById('posterDetailModal')).hide();
                            loadPosterDashboard();
                        },
                        error: function (xhr) {
                            alert("Failed to save changes: " + (xhr.responseJSON?.detail || "Update Error"));
                        }
                    });
                });

                const myModal = new bootstrap.Modal(document.getElementById('posterDetailModal'));
                myModal.show();
            },
            error: function () {
                alert("Failed to load details for poster analysis: " + id);
            }
        });
    };

    window.reanalyzePoster = function (id) {
        $("#processing-overlay").removeClass("d-none");
        $("#processing-title").text("Re-Analyzing Poster");
        $("#processing-status").text("Regenerating transcription and analysis tokens...");
        $("#processing-progress").css("width", "50%");

        $.ajax({
            url: `${API_ROOT}/poster/${id}/reanalyze`,
            type: "POST",
            beforeSend: function (xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function () {
                $("#processing-overlay").addClass("d-none");
                console.log("Poster analysis regenerated.");
                loadPosterDashboard();
                loadPosterDetails(id);
            },
            error: function (xhr) {
                $("#processing-overlay").addClass("d-none");
                alert("Re-analysis failed: " + (xhr.responseJSON?.detail || "Error"));
            }
        });
    };

    window.deletePoster = function (id) {
        if (!confirm("Are you sure you want to permanently delete this poster and its analysis records?")) {
            return;
        }

        $.ajax({
            url: `${API_ROOT}/poster/${id}`,
            type: "DELETE",
            beforeSend: function (xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function () {
                console.log("Poster analysis deleted.");
                loadPosterDashboard();
                
                // Clear active view details if it matches the deleted ID
                $("#poster-results-placeholder").removeClass("d-none");
                $("#poster-results-content").addClass("d-none");
            },
            error: function (xhr) {
                alert("Failed to delete poster: " + (xhr.responseJSON?.detail || "Delete Error"));
            }
        });
    };

    // ==========================================
    // THEME LIGHT/DARK CONTROLLERS
    // ==========================================

    $("#btn-toggle-theme").on("click", function () {
        if ($("body").hasClass("dark-theme")) {
            applyLightTheme();
            localStorage.setItem("pasas_theme", "light");
        } else {
            applyDarkTheme();
            localStorage.setItem("pasas_theme", "dark");
        }
        
        if ($("#view-dashboard").is(":visible")) {
            loadDashboardData();
        }
    });

    function applyDarkTheme() {
        $("body").addClass("dark-theme");
        $("#icon-moon").addClass("d-none");
        $("#icon-sun").removeClass("d-none");
        $("#theme-toggle-text").text(translations["theme_light"] || "Light Mode");
    }

    function applyLightTheme() {
        $("body").removeClass("dark-theme");
        $("#icon-sun").addClass("d-none");
        $("#icon-moon").removeClass("d-none");
        $("#theme-toggle-text").text(translations["theme_night"] || "Night Mode");
    }

    // ==========================================
    // DAILY REPORT MANUAL FORM SUBMISSION
    // ==========================================

    const activeReps = [
        "Sankarapandian",
        "Periyar Selvam",
        "Bala Murugan",
        "Rajeshwaran",
        "Vinoth Kumar",
        "Parthiban",
        "Sri Ram"
    ];

    $("#btn-open-create-report").on("click", function () {
        // Prepopulate representatives dropdown
        const repSelect = $("#form-rep");
        repSelect.empty().append('<option value="" disabled selected>Select representative</option>');
        activeReps.forEach(rep => {
            repSelect.append(`<option value="${rep}">${rep}</option>`);
        });

        // Set default date to today
        const today = new Date().toISOString().split('T')[0];
        $("#form-date").val(today);
        $("#form-stock-date").val(today);

        // Reset form
        $("#create-report-form")[0].reset();
        $("#form-date").val(today);
        $("#form-stock-date").val(today);

        const myModal = new bootstrap.Modal(document.getElementById('createReportModal'));
        myModal.show();
    });

    $("#create-report-form").on("submit", function (e) {
        e.preventDefault();

        function formatSalesRaw() {
            const prod = $("#form-sales-product").val();
            const qty = $("#form-sales-qty").val();
            const amt = $("#form-sales-amount").val();
            if (!prod) return "None";
            return `${qty || 1}x ${prod} (₹${Number(amt || 0).toLocaleString("en-IN")})`;
        }
        function formatCollectionRaw() {
            const amt = $("#form-coll-amount").val();
            const mode = $("#form-coll-mode").val();
            const status = $("#form-coll-status").val();
            if (!amt) return "None";
            return `₹${Number(amt).toLocaleString("en-IN")} via ${mode} (${status})`;
        }
        function formatCompetitionRaw() {
            const name = $("#form-comp-name").val();
            if (!name) return "None";
            return name;
        }
        function formatProductRaw() {
            const name = $("#form-prod-name").val();
            if (!name) return "None";
            return name;
        }
        function formatPriceListRaw() {
            const prod = $("#form-price-product").val();
            const our = $("#form-price-our").val();
            if (!prod) return "None";
            return `₹${our || 0} / unit (${prod})`;
        }
        function formatOurServicesRaw() {
            const name = $("#form-srv-name").val();
            if (!name) return "None";
            return name;
        }
        function formatOurNewProductsRaw() {
            const name = $("#form-new-name").val();
            if (!name) return "None";
            return name;
        }
        function formatMostSellProductsRaw() {
            const name = $("#form-most-name").val();
            if (!name) return "None";
            return name;
        }
        function formatPendingStockRaw() {
            const name = $("#form-stock-name").val();
            const req = $("#form-stock-req").val();
            if (!name) return "None";
            return `${req || 0} units (${name})`;
        }

        const payload = {
            representative: $("#form-rep").val(),
            date: $("#form-date").val(),
            client_name: $("#form-client").val(),
            summary: $("#form-summary").val(),
            sentiment: $("#form-sentiment").val(),
            priority: $("#form-priority").val(),
            follow_up_date: $("#form-follow-up").val() || null,
            
            // Raw text representations
            sales_raw: formatSalesRaw(),
            collection_raw: formatCollectionRaw(),
            competition_raw: formatCompetitionRaw(),
            product_raw: formatProductRaw(),
            price_list_raw: formatPriceListRaw(),
            our_services_raw: formatOurServicesRaw(),
            our_new_products_raw: formatOurNewProductsRaw(),
            most_sell_products_raw: formatMostSellProductsRaw(),
            pending_stock_raw: formatPendingStockRaw(),
            
            // Structured data for backend stats compatibility
            sales_details: {
                item_name: $("#form-sales-product").val(),
                quantity: $("#form-sales-qty").val() || 0,
                amount: $("#form-sales-amount").val() || 0
            },
            collection_details: {
                amount_collected: $("#form-coll-amount").val() || 0,
                payment_method: $("#form-coll-mode").val(),
                status: $("#form-coll-status").val()
            },
            competition_details: {
                competitor_name: $("#form-comp-name").val(),
                remarks: $("#form-comp-remarks").val()
            },
            product_details: {
                product_name: $("#form-prod-name").val(),
                remarks: $("#form-prod-remarks").val()
            },
            service_details: {
                complaint: $("#form-srv-complaint").val()
            }
        };

        $.ajax({
            url: `${API_ROOT}/reports`,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(payload),
            beforeSend: function (xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function () {
                // Hide modal and refresh views
                bootstrap.Modal.getInstance(document.getElementById('createReportModal')).hide();
                loadAnalysisDataTable();
                loadDashboardData();
                console.log("Daily report submitted successfully.");
            },
            error: function (xhr) {
                alert("Failed to submit daily report: " + (xhr.responseJSON?.detail || "Submission Error"));
            }
        });
    });
});


/* =========================================================================
   LIVE SALES REPRESENTATIVE INSIGHTS (appended via AI)
   ========================================================================= */

let liveInsightsInterval = null;
let lastInsightsData = [];

function getPriorityBadge(priority) {
    if (!priority) return '<span class="badge bg-secondary">Unknown</span>';
    const p = priority.toLowerCase();
    if (p.includes("urgent")) return '<span class="badge bg-danger">🔴 URGENT</span>';
    if (p.includes("high")) return '<span class="badge bg-warning text-dark">🟠 HIGH</span>';
    if (p.includes("low")) return '<span class="badge bg-info text-dark">🟢 LOW</span>';
    return '<span class="badge bg-secondary">🟡 MEDIUM</span>';
}

function getSentimentBadge(sentiment) {
    if (!sentiment) return '<span class="badge bg-secondary">Unknown</span>';
    const s = sentiment.toLowerCase();
    if (s.includes("positive") || s.includes("good")) return '<span class="badge bg-success">🟢 POSITIVE</span>';
    if (s.includes("not") || s.includes("negative") || s.includes("bad")) return '<span class="badge bg-danger">🔴 NOT GOOD</span>';
    return '<span class="badge bg-warning text-dark">🟡 MEDIUM</span>';
}

function renderLiveInsightsCards(insights) {
    const container = $("#live-insights-cards");
    container.empty();
    
    if (!insights || insights.length === 0) {
        container.html('<div class="col-12 text-center text-muted">No live insights available.</div>');
        return;
    }

    lastInsightsData = insights;
    
    let html = "";
    insights.forEach((insight, idx) => {
        if (insight.status === "NO REPORT" || insight.status === "ERROR") {
            html += `
            <div class="col-md-4 mb-3">
                <div class="card h-100 bg-dark border-secondary">
                    <div class="card-body d-flex flex-column justify-content-center align-items-center text-center">
                        <h6 class="text-white mb-3">👤 ${insight.sales_rep}</h6>
                        <div class="text-muted">
                            <i class="bi bi-dash-circle fs-3 d-block mb-2"></i>
                            <span class="fw-bold">⚪ NO REPORT</span><br>
                            <small>Today's report not submitted</small>
                        </div>
                    </div>
                </div>
            </div>`;
        } else {
            let keywordsHtml = "";
            if (insight.important_keywords && Array.isArray(insight.important_keywords)) {
                keywordsHtml = insight.important_keywords.map(kw => `<span class="badge bg-secondary me-1 mb-1">${kw}</span>`).join("");
            }
            
            html += `
            <div class="col-md-4 mb-3">
                <div class="card h-100 custom-modal-bg border-secondary shadow-sm">
                    <div class="card-body d-flex flex-column">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <h6 class="text-white mb-0 fw-bold">👤 ${insight.sales_rep}</h6>
                            <span class="badge bg-success" style="font-size:0.6rem;"><i class="bi bi-circle-fill me-1" style="font-size:0.5rem;"></i>LIVE</span>
                        </div>
                        <div class="text-muted tiny mb-3">Updated: ${insight.last_updated}</div>
                        
                        <div class="mb-3 flex-grow-1">
                            <h6 class="text-warning small fw-bold mb-1">🔥 MOST IMPORTANT POINT</h6>
                            <p class="text-white small mb-3">${insight.most_important_point || "Not reported"}</p>
                            
                            <h6 class="text-info small fw-bold mb-1">🔑 KEYWORDS</h6>
                            <div class="mb-3">${keywordsHtml || "<span class='text-muted small'>None</span>"}</div>
                            
                            <h6 class="text-primary small fw-bold mb-1">💬 SALES REP SPEAK</h6>
                            <p class="text-light small mb-3 fst-italic">"${insight.sales_rep_speak || "Not reported"}"</p>
                            
                            <h6 class="text-success small fw-bold mb-1">➡️ FOLLOW-UP</h6>
                            <p class="text-white small mb-0">${insight.follow_up || "None reported"}</p>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center mt-3 pt-3 border-top border-secondary">
                            <div>
                                ${getPriorityBadge(insight.priority)}
                                ${getSentimentBadge(insight.sentiment)}
                            </div>
                            <button class="btn btn-sm btn-outline-light view-live-insight-btn" data-index="${idx}">View Details</button>
                        </div>
                    </div>
                </div>
            </div>`;
        }
    });
    
    container.html(html);
}

function loadLiveInsights() {
    $.ajax({
        url: `${API_ROOT}/dashboard/live-insights`,
        success: function(res) {
            if (res && res.insights) {
                renderLiveInsightsCards(res.insights);
                const now = new Date();
                $("#live-insights-timestamp").text(`Last updated: ${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`);
            }
        },
        error: function(err) {
            console.error("Failed to load live insights", err);
        }
    });
}

// Start polling
$(document).ready(function() {
    // Initial load
    setTimeout(loadLiveInsights, 1000);
    // Poll every 60 seconds
    liveInsightsInterval = setInterval(loadLiveInsights, 60000);
});

// View Details Modal Trigger
$(document).on("click", ".view-live-insight-btn", function() {
    const idx = $(this).data("index");
    const insight = lastInsightsData[idx];
    if (!insight) return;
    
    $("#insight-modal-rep-name").text(insight.sales_rep);
    $("#insight-modal-time").text(`${insight.report_date} ${insight.last_updated}`);
    
    $("#insight-modal-important-point").text(insight.most_important_point || "Not reported");
    
    let keywordsHtml = "Not reported";
    if (insight.important_keywords && Array.isArray(insight.important_keywords) && insight.important_keywords.length > 0) {
        keywordsHtml = insight.important_keywords.map(kw => `<span class="badge bg-secondary me-1">${kw}</span>`).join("");
    }
    $("#insight-modal-keywords").html(keywordsHtml);
    
    $("#insight-modal-rep-speak").text(`"${insight.sales_rep_speak || "Not reported"}"`);
    
    $("#insight-modal-customer").text(insight.customer_discussion || "Not reported");
    $("#insight-modal-dealer").text(insight.dealer_discussion || "Not reported");
    $("#insight-modal-sales").text(insight.sales_information || "Not reported");
    $("#insight-modal-collection").text(insight.collection_information || "Not reported");
    $("#insight-modal-competition").text(insight.competition_information || "Not reported");
    $("#insight-modal-product").text(insight.product_information || "Not reported");
    $("#insight-modal-price").text(insight.price_information || "Not reported");
    $("#insight-modal-new-product").text(insight.new_product_information || "Not reported");
    $("#insight-modal-stock").text(insight.stock_information || "Not reported");
    
    $("#insight-modal-followup").text(insight.follow_up || "None reported");
    
    $("#insight-modal-priority").html(getPriorityBadge(insight.priority));
    $("#insight-modal-sentiment").html(getSentimentBadge(insight.sentiment));
    
    const modal = new bootstrap.Modal(document.getElementById('liveInsightsDetailModal'));
    modal.show();
});


/* =========================================================================
   MANUAL VOICE UPLOAD & LOCAL AI ANALYSIS HANDLERS
   ========================================================================= */

let selectedManualFile = null;
let currentUploadedVoiceFileId = null;

// Initialize Date and Time inputs with current date & time
$(document).ready(function() {
    const todayStr = new Date().toISOString().split('T')[0];
    const nowTimeStr = new Date().toTimeString().split(' ')[0].substring(0, 5);
    $("#manual-date-input").val(todayStr);
    $("#manual-time-input").val(nowTimeStr);
});

// File Selection Handler
$(document).on("change", "#manual-voice-file-input", function(e) {
    const files = e.target.files;
    if (files && files.length > 0) {
        handleManualFileSelect(files[0]);
    }
});

// Drag and Drop Handlers
$(document).on("dragover dragenter", "#manual-upload-dropzone", function(e) {
    e.preventDefault();
    e.stopPropagation();
    $(this).addClass("border-primary");
});

$(document).on("dragleave drop", "#manual-upload-dropzone", function(e) {
    e.preventDefault();
    e.stopPropagation();
    $(this).removeClass("border-primary");
});

$(document).on("drop", "#manual-upload-dropzone", function(e) {
    const dt = e.originalEvent.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
        handleManualFileSelect(dt.files[0]);
    }
});

function handleManualFileSelect(file) {
    const MAX_SIZE = 1024 * 1024 * 1024; // 1 GB
    if (file.size > MAX_SIZE) {
        alert("File size exceeds the maximum allowed limit of 1 GB.");
        return;
    }

    const allowedExts = [".txt", ".json", ".csv", ".doc", ".docx", ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".webm"];
    const ext = "." + file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
        alert("Unsupported format. Allowed formats: TXT, JSON, CSV, DOC, WAV, MP3, M4A, AAC, OGG, WEBM.");
        return;
    }

    selectedManualFile = file;
    currentUploadedVoiceFileId = null;

    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    const displaySize = file.size < 1024 * 1024 ? `${(file.size / 1024).toFixed(1)} KB` : `${sizeMB} MB`;
    
    $("#manual-file-name").text(file.name);
    $("#manual-file-meta").text(`${displaySize} | ${ext.replace('.', '').toUpperCase()}`);
    $("#manual-file-details").removeClass("d-none");

    $("#manual-text-active-file").text(file.name);
    $("#manual-text-active-rep").text($("#manual-rep-select").val());

    // If text file (.txt, .json, .csv, .doc, .docx), read content directly into textarea
    if ([".txt", ".json", ".csv", ".doc", ".docx"].includes(ext)) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const textContent = e.target.result || "";
            $("#manual-tamil-summary-textarea").val(textContent);
            $("#tamil-summary-char-count").text(textContent.length.toLocaleString("en-US"));
            
            $("#manual-badge-upload-status").removeClass("bg-secondary bg-danger bg-warning text-dark").addClass("bg-success").text("Text File Loaded");
            $("#manual-badge-ai-status").removeClass("bg-secondary bg-danger bg-warning text-dark").addClass("bg-info text-dark").text("Ready to Analyze");
            $("#tamil-card-status-badge").removeClass("bg-secondary bg-danger").addClass("bg-success").text("🟢 Text Ready for AI Analysis");

            appendSyncLog(`> Uploaded text file '${file.name}' (${textContent.length.toLocaleString()} characters). Content loaded into Tamil Summary box.`);
            updateManualStepLog(`
                <div class="text-success mb-1"><i class="bi bi-file-earmark-text-fill me-1"></i> ✓ Text file '${file.name}' loaded (${textContent.length.toLocaleString()} chars)</div>
                <div class="text-info mb-1"><i class="bi bi-play-circle-fill me-1"></i> Click "Proceed & Analyze" to run Local Ollama AI analysis.</div>
            `);

            // Smooth scroll to Card 3 (Tamil Voice Summary) so user sees content ready
            $('html, body').animate({
                scrollTop: $("#manual-tamil-summary-textarea").offset().top - 120
            }, 400);
        };
        reader.readAsText(file, "UTF-8");
    } else {
        // Audio file
        $("#manual-badge-upload-status").removeClass("bg-success bg-danger").addClass("bg-warning text-dark").text("Ready to Upload");
        $("#manual-badge-ai-status").removeClass("bg-success bg-danger").addClass("bg-secondary").text("Idle");
        $("#btn-manual-analyze-start").prop("disabled", true);
        $("#manual-analysis-step-log").html('<div class="text-info"><i class="bi bi-arrow-up-circle me-1"></i> File selected. Click "Upload Voice Recording" to proceed.</div>');
    }
}

// Remove File Button
$(document).on("click", "#btn-manual-remove-file", function() {
    selectedManualFile = null;
    currentUploadedVoiceFileId = null;
    $("#manual-voice-file-input").val("");
    $("#manual-file-details").addClass("d-none");
    $("#manual-upload-progress-container").addClass("d-none");
    $("#manual-upload-progress-bar").css("width", "0%");

    $("#manual-badge-upload-status").removeClass("bg-success bg-warning text-dark bg-danger").addClass("bg-secondary").text("No File Uploaded");
    $("#manual-badge-ai-status").removeClass("bg-success bg-danger").addClass("bg-secondary").text("Idle");
    $("#manual-text-active-file").text("None");
    $("#manual-text-active-rep").text("-");
    $("#btn-manual-analyze-start").prop("disabled", true);
    $("#manual-analysis-step-log").html('<div class="text-muted fst-italic"><i class="bi bi-info-circle me-1"></i> Upload a recording to enable local AI analysis.</div>');
});

const REP_CLIENT_MAPPING = {
    "Sankarapandian": ["Girish Paints & Hardware", "New Star Traders", "Rajesh Enterprises", "Sri Murugan Paints", "Vinayaga Enterprises", "Coimbatore - Sri Velavan Agencies", "ANDIMADAM - K.SOUNDRARAJAN", "KARUR - BALAJI PAINTS"],
    "Periyar Selvam": ["Classic Agencies", "MSK Hardware", "Modern Paint House", "Pioneer Adhesives", "Rajesh Enterprises", "Sri Lakshmi Agencies", "AMBASAMUDRAM - KR THIRUKATHIRVEL", "CHENNAI - VIJAY ENTERPRISES"],
    "Bala Murugan": ["Alangulam-S. SUDALAMUTHU NADAR", "Arun Traders", "Classic Agencies", "Kumar Traders", "Rajesh Enterprises", "Sri Murugan Paints", "COIMBATORE-DIVYA HARDWARES"],
    "Rajeshwaran": ["Arun Traders", "Classic Agencies", "Ganesh Hardware", "Pioneer Adhesives", "Sri Lakshmi Agencies", "Vinayaga Enterprises", "DHARAPURAM - AMMAN TRADERS"],
    "Vinoth Kumar": ["Girish Paints & Hardware", "Kumar Traders", "MSK Hardware", "Pioneer Adhesives", "Sri Murugan Paints", "Vinayaga Enterprises", "COONOOR-GEMINI HARDWARE STORES"],
    "Parthiban": ["Arun Traders", "Ganesh Hardware", "Modern Paint House", "Rajesh Enterprises", "Royal Paints", "Vinayaga Enterprises", "CHINTHAMANI -MATHA PAINTS"],
    "Sri Ram": ["Arun Traders", "Girish Paints & Hardware", "Green Paints", "Modern Paint House", "Sri Lakshmi Agencies", "Sri Murugan Paints", "COIMBATORE - ARUL HARDWARE"]
};

function updateManualClientDropdown(selectedRep) {
    const clientSelect = $("#manual-client-select");
    if (!clientSelect.length) return;

    if (!selectedRep) {
        selectedRep = $("#manual-rep-select").val() || "Sankarapandian";
    }

    const repMapping = {
        "balamurugan": "Balamurugan",
        "rajeshwaran": "Rajeshwaran",
        "sriram": "Sriram",
        "vinothkumar": "Vinothkumar",
        "parthiban": "Parthiban",
        "periyarselvam": "Periyar Selvam",
        "sankarapandian": "Sankarapandian",
        "santhanapandiyan": "Sankarapandian"
    };

    let dealersToDisplay = [];
    const normSelected = (selectedRep || "").toLowerCase().replace(/[\s\-_]/g, "");

    const masterSource = (typeof window.PDF_MASTER_DEALERS !== "undefined" && window.PDF_MASTER_DEALERS) 
        ? window.PDF_MASTER_DEALERS 
        : ((typeof masterDealersData !== "undefined" && masterDealersData) ? masterDealersData : null);

    if (masterSource) {
        const exactKey = repMapping[normSelected];
        if (exactKey && masterSource[exactKey]) {
            dealersToDisplay = [...masterSource[exactKey]];
        } else if (masterSource[selectedRep]) {
            dealersToDisplay = [...masterSource[selectedRep]];
        } else {
            Object.keys(masterSource).forEach(key => {
                const normKey = key.toLowerCase().replace(/[\s\-_]/g, "");
                if (normKey.includes(normSelected) || normSelected.includes(normKey)) {
                    dealersToDisplay = dealersToDisplay.concat(masterSource[key]);
                }
            });
        }
    }

    if (dealersToDisplay.length === 0 && typeof REP_CLIENT_MAPPING !== "undefined") {
        Object.keys(REP_CLIENT_MAPPING).forEach(key => {
            const normKey = key.toLowerCase().replace(/[\s\-_]/g, "");
            if (normKey.includes(normSelected) || normSelected.includes(normKey)) {
                dealersToDisplay = dealersToDisplay.concat(REP_CLIENT_MAPPING[key]);
            }
        });
    }

    dealersToDisplay = Array.from(new Set(dealersToDisplay)).filter(Boolean).sort();

    if (dealersToDisplay.length === 0) {
        dealersToDisplay = ["Rajesh Enterprises", "General Client", "Classic Agencies", "Sri Murugan Paints"];
    }

    clientSelect.empty();
    dealersToDisplay.forEach((d, idx) => {
        clientSelect.append(`<option value="${d}" class="text-dark bg-white" style="color: #000000 !important; background-color: #ffffff !important;" ${idx === 0 ? 'selected' : ''}>${d}</option>`);
    });
}

// Rep Select Change Handler
$(document).on("change focus", "#manual-rep-select", function() {
    const rep = $(this).val();
    $("#manual-text-active-rep").text(rep);
    updateManualClientDropdown(rep);
});

// Client Select Focus Handler to ensure non-empty options
$(document).on("focus click", "#manual-client-select", function() {
    if ($(this).children("option").length === 0) {
        const currentRep = $("#manual-rep-select").val() || "Sankarapandian";
        updateManualClientDropdown(currentRep);
    }
});

// Initialize client dropdown on page load
$(document).ready(function() {
    setTimeout(function() {
        const initialRep = $("#manual-rep-select").val() || "Sankarapandian";
        updateManualClientDropdown(initialRep);
    }, 200);
});

// Start Upload Handler
$(document).on("click", "#btn-manual-upload-start", function() {
    if (!selectedManualFile) {
        alert("Please select a valid voice recording file (up to 1 GB).");
        return;
    }

    const rep = $("#manual-rep-select").val();
    const client = $("#manual-client-select").val() || $("#manual-client-input").val() || "General Client";
    const dateVal = $("#manual-date-input").val();
    const timeVal = $("#manual-time-input").val();

    appendSyncLog("> Manual voice upload started.");

    const formData = new FormData();
    formData.append("file", selectedManualFile);
    formData.append("representative", rep);
    formData.append("client_name", client);
    formData.append("date", dateVal);
    formData.append("time", timeVal);

    $("#manual-upload-progress-container").removeClass("d-none");
    $("#manual-upload-progress-bar").css("width", "0%");
    $("#manual-upload-status-text").text("Uploading...");
    $("#manual-upload-percent-text").text("0%");
    $("#btn-manual-upload-start").prop("disabled", true);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_ROOT}/sync/manual-upload`, true);
    const token = (typeof authToken !== "undefined" && authToken) ? authToken : localStorage.getItem("pasas_token");
    if (token) {
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            $("#manual-upload-progress-bar").css("width", `${percent}%`);
            $("#manual-upload-percent-text").text(`${percent}%`);
            if (percent >= 100) {
                $("#manual-upload-status-text").text("Processing Tamil Speech-to-Text... Please wait.");
                $("#manual-badge-upload-status").removeClass("bg-secondary bg-danger").addClass("bg-warning text-dark").text("Processing STT...");
            }
        }
    };

    xhr.onload = function() {
        $("#btn-manual-upload-start").prop("disabled", false);
        if (xhr.status === 200) {
            try {
                const res = JSON.parse(xhr.responseText);
                currentUploadedVoiceFileId = res.id || res.voice_file_id;
                $("#manual-upload-status-text").text("Tamil voice recording transcribed via ElevenLabs.");
                $("#manual-upload-percent-text").text("100%");
                $("#manual-badge-upload-status").removeClass("bg-warning text-dark bg-secondary bg-danger").addClass("bg-success").text("Transcribed");
                $("#btn-manual-analyze-start").prop("disabled", false);

                // Populate Tamil Summary Textarea with Full Tamil Transcript
                const fullTranscript = res.transcript || res.tamil_summary || `வணக்கம்! விற்பனை பிரதிநிதி ${res.representative || ''}, வாடிக்கையாளர் ${res.client_name || ''} அவர்களுடன் குரல் உரையாடல் நடத்தினார்.`;
                $("#manual-tamil-summary-textarea").val(fullTranscript);
                $("#tamil-summary-char-count").text(fullTranscript.length.toLocaleString("en-US"));

                // Update Card 3: Tamil Voice Summary & Proceed & Analyze Button
                $("#tamil-card-text-content").html(`<div class="p-3 bg-light rounded border border-secondary-subtle text-dark fw-bold fs-6" style="white-space: pre-wrap;"><i class="bi bi-chat-quote me-2 text-primary"></i>${fullTranscript}</div>`);
                $("#tamil-card-status-badge").removeClass("bg-secondary bg-danger").addClass("bg-success").text("🟢 Transcript Ready for Local AI Analysis");
                $("#btn-proceed-and-analyze").prop("disabled", false);

                appendSyncLog(`> ElevenLabs Tamil STT completed. Full transcript (${fullTranscript.length.toLocaleString()} chars) loaded into Tamil Summary box.`);
                $("#manual-analysis-step-log").html('<div class="text-success"><i class="bi bi-check-circle me-1"></i> ElevenLabs Tamil transcription completed. Click "Proceed & Analyze" to view 10-category analysis on Dashboard.</div>');
            } catch (err) {
                alert("Error parsing upload response.");
            }
        } else {
            let detail = "Upload failed.";
            try { detail = JSON.parse(xhr.responseText).detail || detail; } catch(e){}
            alert(`Upload Error: ${detail}`);
            appendSyncLog(`> Manual voice upload failed: ${detail}`);
            $("#manual-upload-status-text").text("Upload failed.");
            $("#manual-badge-upload-status").removeClass("bg-warning text-dark bg-success").addClass("bg-danger").text("Failed");
        }
    };

    xhr.onerror = function() {
        $("#btn-manual-upload-start").prop("disabled", false);
        alert("Network error during manual voice upload.");
        appendSyncLog("> Manual voice upload failed: Network Error.");
        $("#manual-upload-status-text").text("Upload error.");
    };

    xhr.send(formData);
});

// Live Character Counter for Tamil Voice Summary Textarea
$(document).on("input keyup", "#manual-tamil-summary-textarea", function() {
    const len = $(this).val().length;
    $("#tamil-summary-char-count").text(len.toLocaleString("en-US"));
});

let currentAnalysisRequestId = null;
let currentAnalysisData = null;

// Start Analysis & Proceed to Dashboard Handler
$(document).on("click", "#btn-manual-analyze-start, #btn-proceed-and-analyze", function() {
    const rep = $("#manual-rep-select").val();
    const client = $("#manual-client-select").val() || $("#manual-client-input").val() || "General Client";
    const dateVal = $("#manual-date-input").val();
    
    let tamilSummaryText = ($("#manual-tamil-summary-textarea").val() || "").trim();
    if (!tamilSummaryText) {
        const altText = ($("#tamil-card-text-content").text() || "").trim();
        if (altText && !altText.includes("Upload a voice recording") && !altText.includes("ஒலிப்பதிவை பதிவேற்றிய பிறகு")) {
            tamilSummaryText = altText;
        }
    }

    if (!rep) {
        alert("Please select a Sales Representative.");
        return;
    }

    if (!client) {
        alert("Please select a Client.");
        return;
    }

    // Reset current analysis state before starting new analysis (Requirement #3 & #4)
    currentAnalysisData = null;
    currentAnalysisRequestId = (typeof crypto !== "undefined" && crypto.randomUUID) ? crypto.randomUUID() : ("req-" + Date.now() + "-" + Math.random().toString(36).substring(2, 9));
    const activeRequestId = currentAnalysisRequestId;

    // Check if text is entered in the Tamil Summary Textarea
    if (tamilSummaryText && tamilSummaryText.length > 0) {
        $("#btn-manual-analyze-start, #btn-proceed-and-analyze").prop("disabled", true);
        $("#manual-badge-ai-status").removeClass("bg-secondary bg-success bg-danger").addClass("bg-warning text-dark").text("Analyzing Text...");
        $("#tamil-card-status-badge").removeClass("bg-secondary bg-success").addClass("bg-warning text-dark").text("Analyzing New Conversation...");

        appendSyncLog(`> [${activeRequestId.substring(0, 8)}] Local Ollama AI text analysis pipeline started.`);
        updateManualStepLog(`
            <div class="text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i> ✓ Tamil summary received (${tamilSummaryText.length.toLocaleString()} chars)</div>
            <div class="text-info mb-1"><i class="bi bi-send-fill me-1"></i> ✓ Sending to local Ollama AI model</div>
            <div class="text-info mb-1"><i class="bi bi-hourglass-split me-1"></i> ⏳ Analyzing new conversation & extracting sales insights...</div>
        `);

        $.ajax({
            url: `${API_ROOT}/api/voice-summary/analyze`,
            type: "POST",
            data: {
                request_id: activeRequestId,
                representative: rep,
                client_name: client,
                tamil_summary: tamilSummaryText,
                date: dateVal
            },
            success: function(res) {
                // Prevent race conditions: Ignore response if a newer request was made (Requirement #5)
                if (activeRequestId !== currentAnalysisRequestId) {
                    console.log("Ignoring out-of-order analysis response for request:", activeRequestId);
                    return;
                }

                currentAnalysisData = res;
                $("#btn-manual-analyze-start, #btn-proceed-and-analyze").prop("disabled", false);
                $("#manual-badge-ai-status").removeClass("bg-warning text-dark bg-danger").addClass("bg-success").text("Completed");
                $("#tamil-card-status-badge").removeClass("bg-warning text-dark bg-danger").addClass("bg-success").text("Analyzed & Live on Dashboard");

                appendSyncLog(`> [${activeRequestId.substring(0, 8)}] Local AI text analysis completed successfully. Updating Dashboard...`);
                
                let stepLogHtml = `
                    <div class="text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i> ✓ Tamil summary received</div>
                    <div class="text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i> ✓ Processed by Local Ollama AI</div>
                    <div class="text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i> ✓ Saved as new record (ID: ${res.report_id})</div>
                    <div class="text-success fw-bold mb-2"><i class="bi bi-check-circle-fill me-1"></i> ✓ Dashboard metrics updated! Redirecting to Dashboard...</div>
                `;
                updateManualStepLog(stepLogHtml);

                // Auto-refresh Dashboard metrics
                if (typeof loadDashboardData === "function") loadDashboardData();
                if (typeof loadRankingData === "function") loadRankingData();
                if (typeof loadSyncStatus === "function") loadSyncStatus();

                setTimeout(() => {
                    $(".menu-item[data-target='view-dashboard']").click();
                }, 800);
            },
            error: function(xhr) {
                if (activeRequestId !== currentAnalysisRequestId) return;
                $("#btn-manual-analyze-start, #btn-proceed-and-analyze").prop("disabled", false);
                $("#manual-badge-ai-status").removeClass("bg-warning text-dark bg-success").addClass("bg-danger").text("Failed");
                $("#tamil-card-status-badge").removeClass("bg-warning text-dark bg-success").addClass("bg-danger").text("Analysis Failed");

                let detail = "AI Analysis Error";
                try { detail = xhr.responseJSON?.detail || detail; } catch(e){}

                appendSyncLog(`> Local AI text analysis failed: ${detail}`);
                updateManualStepLog(`
                    <div class="text-danger mb-1"><i class="bi bi-exclamation-triangle-fill me-1"></i> Analysis Failed: ${detail}</div>
                    <button class="btn btn-xs btn-outline-warning mt-2" onclick="$('#btn-proceed-and-analyze').click()"><i class="bi bi-arrow-clockwise me-1"></i> Retry Analysis</button>
                `);
            }
        });
        return;
    }

    // Fallback: Check if voice file recording was uploaded
    if (!currentUploadedVoiceFileId) {
        alert("Please paste the Tamil voice summary in the text area or upload a voice recording before analyzing.");
        return;
    }

    $("#btn-manual-analyze-start, #btn-proceed-and-analyze").prop("disabled", true);
    $("#manual-badge-ai-status").removeClass("bg-secondary bg-success bg-danger").addClass("bg-warning text-dark").text("Analyzing...");
    $("#tamil-card-status-badge").removeClass("bg-secondary bg-success").addClass("bg-warning text-dark").text("Analyzing AI Pipeline...");

    appendSyncLog("> Local AI pipeline started.");
    updateManualStepLog(`
        <div class="text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i> ✓ Audio uploaded</div>
        <div class="text-info mb-1"><i class="bi bi-hourglass-split me-1"></i> ⏳ Analyzing conversation & redirecting to Dashboard...</div>
    `);

    $.ajax({
        url: `${API_ROOT}/sync/manual-analyze/${currentUploadedVoiceFileId}`,
        type: "POST",
        data: {
            representative: rep,
            client_name: client,
            date: dateVal
        },
        success: function(res) {
            $("#btn-manual-analyze-start, #btn-proceed-and-analyze").prop("disabled", false);
            $("#manual-badge-ai-status").removeClass("bg-warning text-dark bg-danger").addClass("bg-success").text("Completed");
            $("#tamil-card-status-badge").removeClass("bg-warning text-dark bg-danger").addClass("bg-success").text("Analyzed & Live on Dashboard");

            appendSyncLog("> Local AI analysis completed successfully. Redirecting to Dashboard...");
            
            let partialResultsHtml = `
                <div class="text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i> ✓ Audio uploaded</div>
                <div class="text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i> ✓ Transcribed Tamil audio</div>
                <div class="text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i> ✓ Analyzed with Ollama</div>
                <div class="text-success fw-bold mb-2"><i class="bi bi-check-circle-fill me-1"></i> ✓ Analysis complete! Showing results on Dashboard...</div>
            `;
            updateManualStepLog(partialResultsHtml);

            // Refresh Dashboard data and automatically switch to Dashboard view
            if (typeof loadDashboardData === "function") loadDashboardData();
            if (typeof loadRankingData === "function") loadRankingData();
            if (typeof loadSyncStatus === "function") loadSyncStatus();

            setTimeout(() => {
                $(".menu-item[data-target='view-dashboard']").click();
            }, 800);
        },
        error: function(xhr) {
            $("#btn-manual-analyze-start, #btn-proceed-and-analyze").prop("disabled", false);
            $("#manual-badge-ai-status").removeClass("bg-warning text-dark bg-success").addClass("bg-danger").text("Failed");
            $("#tamil-card-status-badge").removeClass("bg-warning text-dark bg-success").addClass("bg-danger").text("Analysis Failed");

            let detail = "AI Analysis Error";
            try { detail = xhr.responseJSON?.detail || detail; } catch(e){}

            appendSyncLog(`> Manual AI analysis failed: ${detail}`);
            updateManualStepLog(`
                <div class="text-danger mb-1"><i class="bi bi-exclamation-triangle-fill me-1"></i> Analysis Failed: ${detail}</div>
                <button class="btn btn-xs btn-outline-warning mt-2" onclick="$('#btn-proceed-and-analyze').click()"><i class="bi bi-arrow-clockwise me-1"></i> Retry Analysis</button>
            `);
        }
    });
});

function updateManualStepLog(htmlContent) {
    $("#manual-analysis-step-log").html(htmlContent);
}

function appendSyncLog(msg) {
    const consoleBox = $("#sync-logs-console");
    if (consoleBox.length) {
        consoleBox.append(`<div>${msg}</div>`);
        consoleBox.scrollTop(consoleBox[0].scrollHeight);
    }
}
