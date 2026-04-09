/* CyberPulse — Frontend JavaScript v3.0
   No frameworks. Pure vanilla JS. */

(function () {
    "use strict";

    // ───────── Sidebar Toggle ─────────

    var sidebar = document.getElementById("sidebar");
    var mainWrapper = document.getElementById("main-wrapper");
    var toggleBtn = document.getElementById("sidebar-toggle");

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener("click", function () {
            if (window.innerWidth <= 768) {
                // Mobile: slide in/out
                sidebar.classList.toggle("open");
            } else {
                // Desktop: collapse sidebar
                sidebar.classList.toggle("collapsed");
                mainWrapper && mainWrapper.classList.toggle("expanded");
            }
        });

        // Close sidebar on mobile when clicking outside
        document.addEventListener("click", function (e) {
            if (window.innerWidth <= 768 && sidebar.classList.contains("open")) {
                if (!sidebar.contains(e.target) && e.target !== toggleBtn && !toggleBtn.contains(e.target)) {
                    sidebar.classList.remove("open");
                }
            }
        });
    }

    // ───────── Scan Form ─────────

    var scanForm = document.getElementById("scan-form");
    if (scanForm) {
        var scanTypeSelect = scanForm.querySelector('[name="scan_type"]');
        var customModulesDiv = document.getElementById("custom-modules");
        var submitBtn = document.getElementById("submit-btn");
        var totalCostSpan = document.getElementById("total-cost");

        function calculateCost() {
            if (!totalCostSpan) return;
            var MARKUP = 8;  // market price factor vs AI token cost
            var total = 0;
            document.querySelectorAll('.module-card input[type="checkbox"]').forEach(function (cb) {
                if (cb.checked && cb.dataset.cost) {
                    total += parseFloat(cb.dataset.cost) || 0;
                }
            });
            totalCostSpan.textContent = "\u20ac" + (total * MARKUP).toFixed(2);
        }

        if (scanTypeSelect && customModulesDiv) {
            scanTypeSelect.addEventListener("change", function () {
                customModulesDiv.style.display = this.value === "custom" ? "block" : "none";
                if (this.value === "custom") calculateCost();
            });
        }

        // ── Scan Mode Tabs (black/gray/white box) ──
        var modeTabs = document.querySelectorAll('.scan-mode-tab');
        var grayPanel = document.getElementById('creds-graybox');
        var whitePanel = document.getElementById('creds-whitebox');
        modeTabs.forEach(function(tab) {
            tab.addEventListener('click', function() {
                modeTabs.forEach(function(t) { t.classList.remove('active'); });
                tab.classList.add('active');
                var mode = tab.dataset.mode;
                if (grayPanel) grayPanel.style.display = mode === 'graybox' ? 'block' : 'none';
                if (whitePanel) whitePanel.style.display = mode === 'whitebox' ? 'block' : 'none';
            });
        });

        document.querySelectorAll('.module-card input[type="checkbox"]').forEach(function (cb) {
            cb.addEventListener("change", calculateCost);
        });

        scanForm.addEventListener("submit", function () {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner"></span> Starten\u2026';
            }
        });

        var selectAllBtn = document.getElementById("select-all-modules");
        var deselectAllBtn = document.getElementById("deselect-all-modules");
        if (selectAllBtn) {
            selectAllBtn.addEventListener("click", function () {
                document.querySelectorAll('.module-card input[type="checkbox"]').forEach(function (cb) { cb.checked = true; });
                calculateCost();
            });
        }
        if (deselectAllBtn) {
            deselectAllBtn.addEventListener("click", function () {
                document.querySelectorAll('.module-card input[type="checkbox"]').forEach(function (cb) { cb.checked = false; });
                calculateCost();
            });
        }

        calculateCost();
    }


    // ───────── Scan Progress (SSE) ─────────

    var progressContainer = document.getElementById("progress-container");
    if (progressContainer) {
        var scanId = progressContainer.dataset.scanId;
        if (!scanId) return;

        var terminalOutput = document.getElementById("terminal-output");
        var progressFill = document.getElementById("progress-fill");
        var progressPercent = document.getElementById("progress-percent");
        var progressLabel = document.getElementById("progress-label");
        var statusBar = document.getElementById("scan-status");
        var modulesDone = document.getElementById("modules-done");
        var startTimeEl = document.getElementById("scan-start-time");
        var etaEl = document.getElementById("eta-display");
        var timelineList = document.getElementById("module-timeline-list");

        var totalModules = 0;
        var completedModules = 0;
        var startTime = Date.now();
        var moduleNames = {};

        if (startTimeEl) {
            startTimeEl.textContent = new Date().toLocaleTimeString("nl-NL");
        }

        function addLog(text, cls) {
            if (!terminalOutput) return;
            var line = document.createElement("div");
            line.className = "log-line";
            var ts = new Date().toLocaleTimeString("nl-NL");
            line.innerHTML = '<span class="log-ts">[' + ts + ']</span><span class="' + (cls || "log-info") + '">' + escapeHtml(text) + "</span>";
            terminalOutput.appendChild(line);
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        }

        function updateProgress(done, total) {
            if (total <= 0) return;
            var pct = Math.round((done / total) * 100);
            if (progressFill) progressFill.style.width = pct + "%";
            if (progressPercent) progressPercent.textContent = pct + "%";
            if (progressLabel) progressLabel.textContent = done + " / " + total + " modules";
            if (modulesDone) modulesDone.textContent = done;
        }

        function updateEta() {
            if (!etaEl || completedModules <= 0 || totalModules <= 0) return;
            var elapsed = (Date.now() - startTime) / 1000;
            var remaining = totalModules - completedModules;
            if (remaining <= 0) { etaEl.textContent = "Klaar"; return; }
            var etaSecs = Math.round((elapsed / completedModules) * remaining);
            var m = Math.floor(etaSecs / 60);
            var s = etaSecs % 60;
            etaEl.textContent = (m > 0 ? m + "m " : "") + s + "s";
        }

        function tlItem(moduleId) {
            return document.getElementById("tl-" + moduleId);
        }

        function setStatus(text) {
            if (statusBar) statusBar.innerHTML = '<span class="pulse-dot"></span>' + escapeHtml(text);
        }

        var evtSource = new EventSource("/api/scan/" + encodeURIComponent(scanId) + "/stream");

        evtSource.onmessage = function (event) {
            var data;
            try { data = JSON.parse(event.data); } catch (e) { return; }

            switch (data.type) {
                case "scan_start":
                    totalModules = (data.modules || []).length;
                    startTime = Date.now();
                    addLog("Scan gestart voor " + (data.target || ""), "log-success");
                    addLog("Type: " + (data.scan_type || "") + "  |  Modules: " + totalModules, "log-info");
                    setStatus("Scan bezig\u2026");
                    // Populate module timeline
                    if (timelineList && totalModules > 0) {
                        timelineList.innerHTML = "";
                        (data.modules || []).forEach(function(mId) {
                            var li = document.createElement("li");
                            li.className = "timeline-item pending";
                            li.id = "tl-" + mId;
                            li.innerHTML = '<span class="timeline-dot"></span><span class="timeline-text">M' + mId + '</span>';
                            timelineList.appendChild(li);
                        });
                    }
                    break;
                case "module_start":
                    moduleNames[data.module_id] = data.name || ("M" + data.module_id);
                    addLog("\u25b6 Module " + (data.module_id || "") + " \u2014 " + (data.name || ""), "log-info");
                    var tl = tlItem(data.module_id);
                    if (tl) {
                        tl.className = "timeline-item running";
                        tl.querySelector(".timeline-text").textContent = moduleNames[data.module_id];
                        tl.scrollIntoView({ block: "nearest", behavior: "smooth" });
                    }
                    break;
                case "module_done":
                    completedModules++;
                    var dur = data.duration ? data.duration.toFixed(1) + "s" : "?";
                    addLog("\u2713 Module " + (data.module_id || "") + " klaar \u2014 " + (data.findings_count || 0) + " bevindingen (" + dur + ")", "log-success");
                    updateProgress(completedModules, totalModules);
                    var tlDone = tlItem(data.module_id);
                    if (tlDone) {
                        tlDone.className = "timeline-item done";
                        var doneLabel = (moduleNames[data.module_id] || ("M" + data.module_id));
                        if (data.findings_count) doneLabel += " \u2014 " + data.findings_count;
                        tlDone.querySelector(".timeline-text").textContent = doneLabel;
                    }
                    updateEta();
                    break;
                case "module_error":
                    completedModules++;
                    addLog("\u2717 Module " + (data.module_id || "") + " fout: " + (data.error || "onbekend"), "log-error");
                    updateProgress(completedModules, totalModules);
                    var tlErr = tlItem(data.module_id);
                    if (tlErr) tlErr.className = "timeline-item error";
                    updateEta();
                    break;
                case "scan_complete":
                    addLog("Scan afgerond \u2014 " + (data.total_findings || 0) + " bevindingen totaal", "log-success");
                    updateProgress(totalModules, totalModules);
                    setStatus("Scan compleet. AI-analyse starten\u2026");
                    if (etaEl) etaEl.textContent = "Klaar";
                    break;
                case "analysis_start":
                    addLog("DeepSeek AI analyse gestart\u2026", "log-info");
                    setStatus("AI bezig met analyseren\u2026");
                    break;
                case "analysis_done":
                    addLog("AI analyse voltooid", "log-success");
                    setStatus("Rapport genereren\u2026");
                    break;
                case "analysis_error":
                    addLog("AI analyse fout: " + (data.message || ""), "log-warning");
                    break;
                case "pdf_ready":
                    addLog("PDF rapport gegenereerd", "log-success");
                    break;
                case "redirect":
                    addLog("Klaar! Doorsturen naar rapport\u2026", "log-success");
                    setStatus("Rapport gereed \u2714");
                    evtSource.close();
                    setTimeout(function () { window.location.href = data.url; }, 1200);
                    break;
                case "error":
                    addLog("Fout: " + (data.message || "Onbekende fout"), "log-error");
                    setStatus("Fout opgetreden");
                    evtSource.close();
                    break;
            }
        };

        evtSource.onerror = function () {
            evtSource.close();
            addLog("Verbinding verbroken", "log-warning");
            setStatus("Verbinding verbroken");
        };
    }


    // ───────── AI Analysis Streaming ─────────

    var analysisContainer = document.getElementById("ai-analysis-stream");
    if (analysisContainer) {
        var analysisScanId = analysisContainer.dataset.scanId;
        if (analysisScanId) {
            var streamEl = analysisContainer.querySelector(".ai-stream");
            if (streamEl) {
                var cursor = document.createElement("span");
                cursor.className = "cursor";

                var aSource = new EventSource("/api/scan/" + encodeURIComponent(analysisScanId) + "/analysis/stream");

                aSource.onmessage = function (event) {
                    var data;
                    try { data = JSON.parse(event.data); } catch (e) { return; }

                    if (data.type === "chunk") {
                        streamEl.textContent += data.text;
                        streamEl.appendChild(cursor);
                        streamEl.scrollTop = streamEl.scrollHeight;
                    } else if (data.type === "done") {
                        if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
                        aSource.close();
                    } else if (data.type === "error") {
                        streamEl.textContent += "\n\nFout: " + (data.message || "");
                        if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
                        aSource.close();
                    }
                };

                aSource.onerror = function () {
                    if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
                    aSource.close();
                };
            }
        }
    }


    // ───────── Helpers ─────────

    function escapeHtml(text) {
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
})();
