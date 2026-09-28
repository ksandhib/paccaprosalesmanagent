/**
 * PaccaPro AI Sales Analysis System (PASAS)
 * Frontend SPA Core Controller with i18n English/Tamil support
 */

$(document).ready(function () {
    const API_ROOT = window.location.origin;

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
                        const fmt = val => (!val || val === 0) ? '<span class="text-muted">-</span>' : `INR ${val.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
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
            },
            error: function (xhr) {
                console.error("Dashboard loading failed", xhr);
            }
        });
    }

    let currentRankingPeriod = "all";
    let cachedRankingData = [];

    function loadRankingData(period = "all") {
        currentRankingPeriod = period;
        $.ajax({
            url: `${API_ROOT}/dashboard/ranking?period=${period}`,
            type: "GET",
            beforeSend: function(xhr) {
                xhr.setRequestHeader("Authorization", "Bearer " + authToken);
            },
            success: function (res) {
                cachedRankingData = res;
                renderRankingTable(res);
            },
            error: function (xhr) {
                console.error("Failed to load ranking data", xhr);
            }
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
            const percentageText = hasData ? `${row.percentage}%` : "-";
            const levelText = hasData ? row.level : "No Data";
            
            const salesStars = hasData ? renderStars(row.scores.sales) : "☆☆☆☆☆";
            const collStars = hasData ? renderStars(row.scores.collection) : "☆☆☆☆☆";
            const compStars = hasData ? renderStars(row.scores.competition) : "☆☆☆☆☆";
            const prodStars = hasData ? renderStars(row.scores.product) : "☆☆☆☆☆";
            const priceStars = hasData ? renderStars(row.scores.price_list) : "☆☆☆☆☆";
            const servStars = hasData ? renderStars(row.scores.our_services) : "☆☆☆☆☆";
            const newpStars = hasData ? renderStars(row.scores.our_new_products) : "☆☆☆☆☆";
            const msStars = hasData ? renderStars(row.scores.most_sell_products) : "☆☆☆☆☆";
            const stockStars = hasData ? renderStars(row.scores.pending_stock) : "☆☆☆☆☆";
            const fupStars = hasData ? renderStars(row.scores.follow_up_date) : "☆☆☆☆☆";

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
                    <td><strong class="text-warning">${row.total_stars} ★</strong></td>
                    <td><span class="badge ${getLevelBadgeClass(row.level)}">${levelText} (${percentageText})</span></td>
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
                                return html || `<span class="text-muted small">None</span>`;
                            })()}
                        </div>
                    </td>
                </tr>
            `);
        });
    }

    // Filter selection tab click handler
    $(document).on("click", "#ranking-period-tabs button", function() {
        $("#ranking-period-tabs button").removeClass("active");
        $(this).addClass("active");
        const period = $(this).data("period");
        loadRankingData(period);
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

        charts.repComparison = new Chart(document.getElementById("chart-rep-comparison"), {
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
                        if (!val || val === "None" || val === "N/A") return `<span class="text-muted">None</span>`;
                        const str = String(val);
                        if (str.length > 28) {
                            return `<div class="text-truncate cursor-pointer text-info" style="max-width: 140px;" title="${str.replace(/"/g, '&quot;')}">${str.substring(0, 26)}...</div>`;
                        }
                        return `<div style="max-width: 140px;">${str}</div>`;
                    }
                    
                    tbody.append(`
                        <tr data-report-id="${r.id}">
                            <td><strong>${r.representative}</strong></td>
                            <td class="text-nowrap">${r.date}</td>
                            <td>${r.client_name}</td>
                            <td><div class="text-truncate" style="max-width: 150px;">${r.summary || 'N/A'}</div></td>
                            <td>${formatCell(r.sales_raw)}</td>
                            <td>${formatCell(r.collection_raw)}</td>
                            <td>${formatCell(r.competition_raw)}</td>
                            <td>${formatCell(r.product_raw)}</td>
                            <td>${formatCell(r.price_list_raw)}</td>
                            <td>${formatCell(r.our_services_raw)}</td>
                            <td>${formatCell(r.our_new_products_raw)}</td>
                            <td>${formatCell(r.most_sell_products_raw)}</td>
                            <td>${formatCell(r.pending_stock_raw)}</td>
                            <td class="text-nowrap">${r.follow_up_date || 'N/A'}</td>
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

    function openReportDetailModal(reportId) {
        $.ajax({
            url: `${API_ROOT}/report/${reportId}`,
            type: "GET",
            success: function (r) {
                const catLabel = translations["modal_cat"] || "Field Category";
                const valuesLabel = translations["modal_values"] || "Extracted Values";
                
                let html = `
                    <div class="row g-3 mb-4">
                        <div class="col-md-4">
                            <label class="text-muted tiny text-uppercase">${translations["label_rep"] || 'Sales Representative'}</label>
                            <div class="fw-bold fs-5 text-dark">${r.representative}</div>
                        </div>
                        <div class="col-md-4">
                            <label class="text-muted tiny text-uppercase">${translations["label_client"] || 'Client Business'}</label>
                            <div class="fw-bold fs-5 text-dark">${r.client_name}</div>
                        </div>
                        <div class="col-md-4">
                            <label class="text-muted tiny text-uppercase">${translations["label_date"] || 'Meeting Date'}</label>
                            <div class="fw-bold fs-5 text-dark">${r.date}</div>
                        </div>
                    </div>
                    
                    <div class="mb-4">
                        <label class="text-muted tiny text-uppercase">${translations["th_summary"] || 'AI Pipeline Summary'}</label>
                        <div class="p-3 bg-light rounded border border-secondary-subtle lh-sm text-dark">${r.summary || 'No summary generated.'}</div>
                    </div>
                    
                    <div class="row g-3 mb-4">
                        <div class="col-md-4">
                            <div class="p-2 border border-secondary-subtle rounded bg-light text-center">
                                <span class="text-muted tiny text-uppercase d-block">${translations["th_sentiment"] || 'Sentiment'}</span>
                                <span class="badge tag-badge tag-${r.sentiment.toLowerCase()} fs-6 mt-1">${r.sentiment}</span>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-2 border border-secondary-subtle rounded bg-light text-center">
                                <span class="text-muted tiny text-uppercase d-block">${translations["th_priority"] || 'Priority'}</span>
                                <span class="badge tag-badge tag-${r.priority.toLowerCase()} fs-6 mt-1">${r.priority}</span>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-2 border border-secondary-subtle rounded bg-light text-center">
                                <span class="text-muted tiny text-uppercase d-block">${translations["th_duration"] || 'Voice Duration'}</span>
                                <span class="fw-bold fs-5 mt-1 d-block text-primary">${r.voice_duration.toFixed(1)} seconds</span>
                            </div>
                        </div>
                    </div>
                    
                    <h6 class="text-dark fw-bold mb-2">${translations["panel_reports_sub"] || 'Detailed Structuring'}</h6>
                    <div class="table-responsive mb-4">
                        <table class="table custom-table text-dark bg-light rounded border border-secondary-subtle overflow-hidden">
                            <thead>
                                <tr>
                                    <th>${catLabel}</th>
                                    <th>${valuesLabel}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="text-muted">Sales</td>
                                    <td><strong>${r.sales_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="text-muted">Collection</td>
                                    <td><strong>${r.collection_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="text-muted">Competition</td>
                                    <td><strong>${r.competition_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="text-muted">Product</td>
                                    <td><strong>${r.product_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="text-muted">Price List</td>
                                    <td><strong>${r.price_list_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="text-muted">Our Services</td>
                                    <td><strong>${r.our_services_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="text-muted">Our New Products</td>
                                    <td><strong>${r.our_new_products_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="text-muted">Most Sell Products</td>
                                    <td><strong>${r.most_sell_products_raw || 'None'}</strong></td>
                                </tr>
                                <tr>
                                    <td class="text-muted">Pending Stock</td>
                                    <td><strong>${r.pending_stock_raw || 'None'}</strong></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <h6 class="text-dark fw-bold mb-2">${translations["modal_transcript"] || 'Verbatim Conversation Transcript'}</h6>
                    <div class="conversation-transcript-container p-3 bg-light rounded border border-secondary-subtle" style="max-height: 250px; overflow-y: auto;">
                `;

                if (r.conversations.length === 0) {
                    html += `<p class="text-muted small text-center my-3">No dialogue segments available.</p>`;
                } else {
                    r.conversations.forEach(c => {
                        let speakerClass = "speaker-rep";
                        if (c.speaker === "Client") speakerClass = "speaker-client";
                        else if (c.speaker === "AI Agent") speakerClass = "speaker-ai";

                        html += `
                            <div class="dialog-bubble ${speakerClass}">
                                <div class="tiny fw-bold text-uppercase d-flex justify-content-between mb-1">
                                    <span class="text-dark">${c.speaker}</span>
                                    <span class="text-muted">${formatTime(c.timestamp)}</span>
                                </div>
                                <div class="small text-dark">${c.text}</div>
                            </div>
                        `;
                    });
                }

                html += `
                    </div>
                    <div class="mt-3 text-muted tiny">${translations["modal_registered"] || 'Report registered:'} ${new Date(r.created_at).toLocaleString()}</div>
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
                    showToastNotification("info", "Duplicate poster detected — re-analyzing image with Ollama.");
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

                                if (payload.step === 11) {
                                    // Complete
                                    $("#processing-overlay").addClass("d-none");
                                    showToastNotification("success", "Poster Analysis Complete!");
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
                // Populate local preview results panel
                const scoreText = res.marketing_score ? `<strong class="text-warning fs-5">${res.marketing_score} / 100</strong>` : "N/A";
                $("#res-executive-summary").html(`
                    <strong>Brand:</strong> ${res.brand || "N/A"}<br/>
                    <strong>Product/Service:</strong> ${res.product || "N/A"}<br/>
                    <strong>Main Heading:</strong> ${res.main_heading || "N/A"}<br/>
                    <strong>Sub Heading:</strong> ${res.sub_heading || "N/A"}<br/>
                    <strong>Language:</strong> ${res.language || "N/A"}<br/>
                    <strong>Target Audience:</strong> ${res.target_audience || "N/A"}<br/>
                    <strong>Tone / Style:</strong> ${res.tone || "N/A"}<br/>
                    <strong>Marketing score:</strong> ${scoreText}<br/><br/>
                    <strong>Summary Description:</strong><br/>
                    ${res.summary || "No summary available."}
                `);
                
                $("#res-ocr-text").text(res.ocr_text);

                const infoUl = $("#res-important-info-list");
                infoUl.empty();
                const info = res.important_information || {};
                const analysis = res.marketing_analysis || {};
                
                infoUl.append(`<li><strong>Price:</strong> ${res.price || "N/A"}</li>`);
                infoUl.append(`<li><strong>Offer / Coupon:</strong> ${res.offer || "None"}</li>`);
                infoUl.append(`<li><strong>Location / Venue:</strong> ${info.venue || "N/A"}</li>`);
                infoUl.append(`<li><strong>Phone Numbers:</strong> ${info.phones?.join(", ") || "None"}</li>`);
                infoUl.append(`<li><strong>Contact URL:</strong> ${info.urls?.join(", ") || "None"}</li>`);
                infoUl.append(`<li><strong>Headline Effectiveness:</strong> ${analysis.headline_effectiveness || "N/A"}</li>`);
                infoUl.append(`<li><strong>Visual Appeal:</strong> ${analysis.visual_appeal || "N/A"}</li>`);
                infoUl.append(`<li><strong>Brand Visibility:</strong> ${analysis.brand_visibility || "N/A"}</li>`);
                infoUl.append(`<li><strong>Product Visibility:</strong> ${analysis.product_visibility || "N/A"}</li>`);
                infoUl.append(`<li><strong>CTA Strength:</strong> ${analysis.call_to_action_strength || "N/A"}</li>`);
                infoUl.append(`<li><strong>Readability:</strong> ${analysis.readability || "N/A"}</li>`);

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

                // Hide placeholder, display results content panels
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
                    <td><span class="badge bg-secondary">${item.poster_category || "Marketing"}</span></td>
                    <td>${item.language}</td>
                    <td>${item.uploaded_by}</td>
                    <td>${item.created_at}</td>
                    <td class="text-truncate" style="max-width: 150px;">${item.summary || "N/A"}</td>
                    <td><span class="badge bg-success">Analyzed</span></td>
                    <td>
                        <div class="dropdown">
                            <button class="btn btn-outline-secondary btn-xs dropdown-toggle" type="button" data-bs-toggle="dropdown">Actions</button>
                            <ul class="dropdown-menu dropdown-menu-dark">
                                <li><a class="dropdown-item btn-action-view" href="#" onclick="openPosterDetail(${item.id})">View Details</a></li>
                                <li><a class="dropdown-item text-warning" href="#" onclick="reanalyzePoster(${item.id})">Re-analyze</a></li>
                                <li><a class="dropdown-item text-danger" href="#" onclick="deletePoster(${item.id})">Delete</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item" href="${API_ROOT}/poster/${item.id}/export/pdf" target="_blank">Download PDF</a></li>
                                <li><a class="dropdown-item" href="${API_ROOT}/poster/${item.id}/export/json" target="_blank">Export JSON</a></li>
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
                            showToastNotification("success", "Poster updated successfully.");
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
                showToastNotification("success", "Poster analysis regenerated.");
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
                showToastNotification("success", "Poster analysis deleted.");
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
        "Santhana Pandiyan",
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
                showToastNotification("success", "Daily report submitted successfully.");
            },
            error: function (xhr) {
                alert("Failed to submit daily report: " + (xhr.responseJSON?.detail || "Submission Error"));
            }
        });
    });
});
