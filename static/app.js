document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentSchemaId = "default";
    let schemaCache = {}; // table_name -> table schema details

    // DOM Elements
    const queryInput = document.getElementById("queryInput");
    const charCount = document.getElementById("charCount");
    const runBtn = document.getElementById("runBtn");
    const presetBtns = document.querySelectorAll(".preset-btn");
    const uploadZone = document.getElementById("uploadZone");
    const schemaFileInput = document.getElementById("schemaFileInput");
    const customSchemaInfo = document.getElementById("customSchemaInfo");
    const uploadedFilename = document.getElementById("uploadedFilename");
    const resetSchemaBtn = document.getElementById("resetSchemaBtn");
    const activeSchemaBadge = document.getElementById("activeSchemaBadge");
    const activeSchemaBadgeText = activeSchemaBadge.querySelector("span");
    const resultsMeta = document.getElementById("resultsMeta");
    const resultCount = document.getElementById("resultCount");
    const responseTime = document.getElementById("responseTime");
    const emptyState = document.getElementById("emptyState");
    const loadingState = document.getElementById("loadingState");
    const resultsList = document.getElementById("resultsList");

    // Fetch and cache the default schema tables on load
    fetchDefaultSchema();

    // Textarea Auto-Resize & Character Count
    queryInput.addEventListener("input", () => {
        charCount.textContent = `${queryInput.value.length} characters`;
        
        // Auto-resize
        queryInput.style.height = "auto";
        queryInput.style.height = (queryInput.scrollHeight) + "px";
    });

    // Preset Queries Click
    presetBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            queryInput.value = btn.dataset.query;
            queryInput.dispatchEvent(new Event("input"));
            runQuery();
        });
    });

    // Click run button
    runBtn.addEventListener("click", runQuery);

    // Schema Drag & Drop / Upload
    uploadZone.addEventListener("click", () => schemaFileInput.click());
    
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("dragover");
    });

    uploadZone.addEventListener("dragleave", () => {
        uploadZone.classList.remove("dragover");
    });

    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleSchemaUpload(e.dataTransfer.files[0]);
        }
    });

    schemaFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleSchemaUpload(e.target.files[0]);
        }
    });

    // Reset Schema to Default
    resetSchemaBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        resetToDefaultSchema();
    });

    // --- Core Functions ---

    async function fetchDefaultSchema() {
        try {
            const res = await fetch("/schema/default");
            if (res.ok) {
                const data = await res.json();
                cacheSchemaTables(data.tables);
            }
        } catch (err) {
            console.error("Failed to fetch default schema:", err);
        }
    }

    function cacheSchemaTables(tables) {
        schemaCache = {};
        tables.forEach(t => {
            schemaCache[t.name] = t;
        });
    }

    async function handleSchemaUpload(file) {
        const formData = new FormData();
        formData.append("file", file);

        showLoading();

        try {
            const res = await fetch("/schema/upload", {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Schema upload failed");
            }

            const data = await res.json();
            currentSchemaId = data.schema_id;
            
            // Cache uploaded schema tables
            cacheSchemaTables(data.tables);

            // Update UI
            uploadedFilename.textContent = file.name;
            customSchemaInfo.classList.remove("hidden");
            uploadZone.classList.add("hidden");
            
            activeSchemaBadge.classList.add("custom");
            activeSchemaBadgeText.textContent = `Active Schema: ${file.name}`;
            
            hideLoading();
            showEmpty("Schema uploaded successfully! Type a query to retrieve tables.");
        } catch (err) {
            hideLoading();
            alert(`Error uploading schema: ${err.message}`);
            resetToDefaultSchema();
        }
    }

    function resetToDefaultSchema() {
        currentSchemaId = "default";
        customSchemaInfo.classList.add("hidden");
        uploadZone.classList.remove("hidden");
        schemaFileInput.value = "";
        
        activeSchemaBadge.classList.remove("custom");
        activeSchemaBadgeText.textContent = "Active Schema: Default E-Commerce";
        
        fetchDefaultSchema();
        showEmpty("Reset to default schema. Submit a query to search.");
    }

    async function runQuery() {
        const query = queryInput.value.trim();
        if (!query) {
            alert("Please enter a query first.");
            return;
        }

        // Setup loader UI
        emptyState.classList.add("hidden");
        resultsList.classList.add("hidden");
        resultsMeta.classList.add("hidden");
        loadingState.classList.remove("hidden");
        runBtn.disabled = true;

        const startTime = performance.now();

        try {
            const res = await fetch("/query", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    question: query,
                    schema_id: currentSchemaId
                })
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Query execution failed");
            }

            const data = await res.json();
            const elapsed = Math.round(performance.now() - startTime);

            renderResults(data.tables, elapsed);
        } catch (err) {
            showEmpty(`Error executing search: ${err.message}`);
        } finally {
            runBtn.disabled = false;
        }
    }

    function renderResults(tables, durationMs) {
        loadingState.classList.add("hidden");
        
        if (tables.length === 0) {
            showEmpty("No matching tables found above the confidence threshold.");
            return;
        }

        resultsList.innerHTML = "";
        resultsList.classList.remove("hidden");

        // Update Meta Header
        resultCount.textContent = `${tables.length} table${tables.length > 1 ? "s" : ""} retrieved`;
        responseTime.textContent = `${durationMs}ms`;
        resultsMeta.classList.remove("hidden");

        tables.forEach((item, index) => {
            const tableDetails = schemaCache[item.name] || { description: "No details available.", columns: [] };
            
            const card = document.createElement("div");
            card.className = "result-item";
            
            // Format column badges
            const columnBadges = tableDetails.columns.map(col => {
                let badgeClass = "col-badge";
                let icon = "";
                if (col.is_pk) {
                    badgeClass += " pk";
                    icon = '<i class="fa-solid fa-key" style="margin-right: 3px; font-size:0.65rem;"></i>';
                } else if (col.is_fk) {
                    badgeClass += " fk";
                    icon = '<i class="fa-solid fa-link" style="margin-right: 3px; font-size:0.65rem;"></i>';
                }
                
                let titleAttr = "";
                if (col.ref_table && col.ref_col) {
                    titleAttr = `title="References ${col.ref_table}.${col.ref_col}"`;
                }
                
                return `<span class="${badgeClass}" ${titleAttr}>${icon}${col.name}</span>`;
            }).join("");

            card.innerHTML = `
                <div class="result-header">
                    <div class="rank-badge">${index + 1}</div>
                    <div class="table-identity">
                        <span class="table-name">${item.name}</span>
                    </div>
                    <span class="match-score">Match: ${(item.score * 100).toFixed(0)}%</span>
                    <i class="fa-solid fa-chevron-down toggle-details-icon"></i>
                </div>
                <div class="result-details">
                    <p class="detail-desc">${tableDetails.description || "No description provided."}</p>
                    <div class="detail-columns-header">Columns</div>
                    <div class="columns-flex">
                        ${columnBadges || '<span class="detail-desc" style="font-style:italic;">No columns specified</span>'}
                    </div>
                </div>
            `;

            // Expand/Collapse click
            card.addEventListener("click", () => {
                card.classList.toggle("expanded");
            });

            resultsList.appendChild(card);
        });
    }

    function showLoading() {
        emptyState.classList.add("hidden");
        resultsList.classList.add("hidden");
        resultsMeta.classList.add("hidden");
        loadingState.classList.remove("hidden");
    }

    function hideLoading() {
        loadingState.classList.add("hidden");
    }

    function showEmpty(message) {
        loadingState.classList.add("hidden");
        resultsList.classList.add("hidden");
        resultsMeta.classList.add("hidden");
        
        emptyState.querySelector("p").textContent = message;
        emptyState.classList.remove("hidden");
    }
});
