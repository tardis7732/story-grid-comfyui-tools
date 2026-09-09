import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const css = document.createElement("style");
css.textContent = `
.sg-ui.sg-style-presets{display:flex;gap:6px;align-items:center;padding:4px 0;border:0;border-radius:0;background:transparent;overflow:hidden}.sg-ui.sg-style-presets button{flex:1;white-space:nowrap;background:#35364e;border-color:#62627e}.sg-ui.sg-style-presets button[aria-pressed="true"]{background:#555577;border-color:#aaa9d0;color:white}
.sg-ui{box-sizing:border-box;width:100%;height:100%;padding:12px;color:#e8edf5;background:#171e2a;border:1px solid #354255;border-radius:12px;font:14px/1.45 Inter,Segoe UI,sans-serif;overflow:auto}
.sg-ui *{box-sizing:border-box}.sg-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px}.sg-kicker{font-size:11px;letter-spacing:1.5px;color:#83c8da;font-weight:700}.sg-muted{color:#a8b5c8;font-size:12px}.sg-ui button{font:inherit;font-size:12px;padding:7px 11px;border-radius:7px;background:#26354a;border:1px solid #49617f;color:#e8edf5;cursor:pointer}.sg-ui button:hover{background:#385371}.sg-gallery{display:flex;gap:12px;overflow:auto;padding-bottom:6px}.sg-card{flex:1 0 180px;max-width:320px;background:#222c3c;border:1px solid #39485e;border-radius:9px;overflow:hidden}.sg-card img{display:block;width:100%;height:220px;object-fit:contain;background:#f5f5f2;cursor:zoom-in}.sg-card figcaption{padding:8px 10px;overflow-wrap:anywhere}.sg-card figure{margin:0}.sg-badge{display:inline-block;color:#93dce9;font-size:12px;font-weight:700;margin-right:6px}.sg-error{color:#ffbcaa;padding:8px}.sg-presets{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.sg-board-wrap{height:180px;display:flex;align-items:center;justify-content:center;border-radius:8px;background:#101620;padding:12px}.sg-board{display:grid;gap:3px;background:#8996a7;border:2px solid #8996a7;box-shadow:0 6px 22px #0006}.sg-cell{background:#faf9f4;color:#455262;font:11px/1 Segoe UI,sans-serif;padding:4px;min-width:0;min-height:0;overflow:hidden}.sg-stats{display:flex;gap:8px;margin-top:10px}.sg-stat{flex:1;padding:9px;background:#222e40;border-radius:7px}.sg-stat b{display:block;font-size:16px;color:#f3f6fc}.sg-note{margin-top:8px;min-height:17px;color:#a8b5c8;font-size:12px}.sg-dialog{padding:14px;border:1px solid #566b86;border-radius:12px;background:#1c2635;color:white;max-width:90vw;max-height:92vh}.sg-dialog::backdrop{background:#000b}.sg-dialog img{display:block;max-width:80vw;max-height:78vh;object-fit:contain;background:white}.sg-dialog button{float:right;margin-bottom:10px}
`;
document.head.append(css);

const widget = (node, name) => node.widgets?.find(w => w.name === name);
const value = (node, name, fallback) => widget(node, name)?.value ?? fallback;
function chain(target, name, callback) {
    const previous = target[name];
    target[name] = function (...args) {
        const result = previous?.apply(this, args);
        callback.apply(this, args);
        return result;
    };
}
function watch(node, names, callback) {
    for (const name of names) {
        const w = widget(node, name);
        if (w) chain(w, "callback", callback);
    }
    chain(node, "onConfigure", () => setTimeout(callback, 0));
}
function panel(node, name, height) {
    const element = document.createElement("div");
    element.className = "sg-ui";
    for (const event of ["pointerdown", "wheel", "dblclick"]) {
        element.addEventListener(event, e => e.stopPropagation());
    }
    const dom = node.addDOMWidget(name, "story_grid_preview", element, {
        serialize: false, hideOnZoom: false,
        getMinHeight: () => height, getMaxHeight: () => height,
    });
    dom.computeSize = () => [0, height];
    return element;
}
const stylePresets = [
    {
        label: "연필 스토리보드",
        text: `STYLE:
Professional film production storyboard, hand-drawn pencil sketch on white paper.
Loose graphite linework, rough construction lines, unfinished concept drawing quality.
Black and white only, no color, no shading except minimal pencil hatching.
Simple but readable character faces and anatomy.
Backgrounds are loosely sketched with perspective lines and only essential environmental details.
Dynamic cinematic compositions, varied camera angles, strong sense of movement and action.
Looks like an actual pre-production storyboard drawn quickly by a professional storyboard artist.
Multiple rectangular storyboard panels arranged cleanly on a white page.
Small handwritten shot numbers beside panels.
Occasional rough motion lines and perspective guides.
NOT a finished comic book, NOT polished illustration, NOT manga panels, NOT cel shading.

VISUAL PRIORITY:
Focus on shot composition, camera placement, character blocking, action readability, perspective, and continuity rather than illustration detail.

Rough storyboard thumbnails, graphite pencil, white storyboard paper, production drawing, cinematic blocking, loose sketch lines, monochrome, unfinished previsualization artwork.

No logos, no captions, no speech bubbles, no polished comic rendering, no color.`,
    },
    {
        label: "페인터리 3D",
        text: `STYLE:
Stylized painterly 3D animation, painterly CGI, hand-painted textures, stylized facial proportions, soft cinematic lighting, warm volumetric sunlight, expressive character design, slightly painterly rendering, animated feature film aesthetic.
Rich but controlled color, tactile surfaces, appealing shapes, and expressive faces with consistent character identity and costumes.
Each panel looks like a cinematic frame from a beautifully crafted animated feature film.
Dynamic cinematic compositions, varied camera angles, readable silhouettes, and a strong sense of movement and action.
Arrange the sequence in the rectangular panels of the supplied grid layout.

VISUAL PRIORITY:
Focus on shot composition, camera placement, character blocking, action readability, perspective, and continuity across all shots.

No logos, no captions, no speech bubbles, no pencil sketch rendering, no manga panels, no flat cel shading.`,
    },
    {
        label: "실사 시네마틱",
        text: `STYLE:
Fully photorealistic live-action cinema, realistic human actors, natural facial proportions and anatomy, lifelike skin texture, believable hair, and physically accurate fabric and materials.
Each panel looks like a frame photographed on a professional cinema camera for a live-action feature film.
Natural cinematic lighting, realistic exposure, subtle film grain, restrained film color grading, realistic lens perspective, and motivated depth of field.
Authentic locations, practical environmental detail, and grounded physical action with consistent character identity and costumes.
Dynamic cinematic compositions, varied camera angles, clear character blocking, and a strong sense of movement and action.
Arrange the sequence in the rectangular panels of the supplied grid layout.

VISUAL PRIORITY:
Focus on shot composition, camera placement, character blocking, action readability, perspective, and continuity across all shots.

No logos, no captions, no speech bubbles, no illustration, no animation, no painterly rendering, no stylized CGI, no pencil sketch, no comic or manga rendering.`,
    },
];
function setTextWidget(text, next) {
    text.value = next;
    if (text.element instanceof HTMLTextAreaElement) {
        text.element.dispatchEvent(new Event("input", { bubbles: true }));
        text.element.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
        text.callback?.(next);
    }
}
function neutralizeAssetStyle(node) {
    const joins = (node.getOutputNodes(0) || [])
        .filter(next => next.type === "StringConcatenate")
        .flatMap(next => next.getOutputNodes(0) || []);
    for (const join of joins.filter(next => next.type === "StringConcatenate")) {
        const references = join.inputs.map((_, i) => join.getInputNode(i))
            .find(input => input?.type === "StoryGridReferenceBatch");
        const slot = references?.inputs.findIndex(input => input.name === "asset_descriptions");
        if (slot === undefined || slot < 0) continue;
        const assets = references.getInputNode(slot);
        if (assets?.type !== "PrimitiveStringMultiline") continue;
        const text = widget(assets, "value");
        const oldSentence = "Render everything in the pencil storyboard STYLE below.";
        if (typeof text?.value === "string" && text.value.includes(oldSentence)) {
            setTextWidget(text, text.value.replace(oldSentence, "Render everything in the STYLE below."));
        }
    }
}
function stylePresetButtons(node) {
    if (node.type !== "PrimitiveStringMultiline" || node.properties?.story_grid_style_presets !== true || widget(node, "style_presets")) return;
    const text = widget(node, "value");
    if (!text) return;
    const size = [...node.size];
    const root = panel(node, "style_presets", 44);
    root.classList.add("sg-style-presets");
    root.setAttribute("aria-label", "스타일 프리셋");
    const toolbar = widget(node, "style_presets");
    toolbar.serialize = false;
    node.widgets.splice(node.widgets.indexOf(toolbar), 1);
    node.widgets.splice(node.widgets.indexOf(text), 0, toolbar);
    const update = () => {
        for (let i = 0; i < root.children.length; i++) {
            root.children[i].setAttribute("aria-pressed", String(text.value === stylePresets[i].text));
        }
    };
    for (const preset of stylePresets) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = preset.label;
        button.onclick = () => {
            node.graph?.beforeChange?.();
            setTextWidget(text, preset.text);
            neutralizeAssetStyle(node);
            update();
            node.graph?.afterChange?.();
            node.graph?.change?.();
            node.setDirtyCanvas?.(true, true);
        };
        root.append(button);
    }
    chain(text, "callback", update);
    chain(node, "onSerialize", data => { data.widgets_values = [text.value]; });
    chain(node, "onConfigure", update);
    node.setSize(size);
    update();
}
function openImage(entry) {
    const dialog = document.createElement("dialog");
    dialog.className = "sg-dialog sg-ui";
    const close = document.createElement("button");
    close.textContent = "닫기";
    close.onclick = () => dialog.close();
    const img = document.createElement("img");
    img.src = entry.data_url;
    img.alt = entry.filename;
    dialog.append(close, img);
    dialog.addEventListener("close", () => dialog.remove(), { once: true });
    document.body.append(dialog);
    dialog.showModal();
}
function referenceGallery(node) {
    const root = panel(node, "reference_gallery", 362);
    root.innerHTML = `<div class="sg-head"><div><div class="sg-kicker">REFERENCE LIBRARY</div><div class="sg-muted sg-ref-status">이미지를 불러오는 중…</div></div><button type="button">새로고침</button></div><div class="sg-gallery"></div><div class="sg-errors"></div>`;
    const gallery = root.querySelector(".sg-gallery");
    const status = root.querySelector(".sg-ref-status");
    const errors = root.querySelector(".sg-errors");
    let generation = 0;
    let timer;
    let removed = false;
    async function refresh() {
        const token = ++generation;
        status.textContent = "이미지를 불러오는 중…";
        try {
            const includeGrid = Boolean(value(node, "include_grid_reference", true));
            const response = await api.fetchApi("/story_grid/reference-preview", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ paths: value(node, "reference_image_paths", ""), include_grid_reference: includeGrid }),
            });
            if (!response.ok) throw new Error(`미리보기 응답 ${response.status}`);
            const result = await response.json();
            if (token !== generation || removed) return;
            gallery.replaceChildren(); errors.replaceChildren();
            status.textContent = `${result.images.length}개 어셋 · ${includeGrid ? "Image 1은 그리드, 어셋은 Image 2부터" : "어셋은 Image 1부터"} · 클릭하여 확대`;
            for (const entry of result.images) {
                const card = document.createElement("div");
                card.className = "sg-card";
                const figure = document.createElement("figure");
                const img = document.createElement("img");
                img.src = entry.data_url; img.alt = entry.filename;
                img.onclick = () => openImage(entry);
                const caption = document.createElement("figcaption");
                const badge = document.createElement("span");
                badge.className = "sg-badge"; badge.textContent = `Image ${entry.index}`;
                caption.append(badge, document.createTextNode(entry.filename));
                const dimensions = document.createElement("div");
                dimensions.className = "sg-muted"; dimensions.textContent = `${entry.width} × ${entry.height}`;
                caption.append(dimensions); figure.append(img, caption); card.append(figure); gallery.append(card);
            }
            for (const entry of result.errors) {
                const error = document.createElement("div");
                error.className = "sg-error";
                error.textContent = `Image ${entry.index} · ${entry.filename}: ${entry.message}`;
                errors.append(error);
            }
            if (!result.images.length && !result.errors.length) status.textContent = "위 경로 칸에 이미지 파일을 한 줄에 하나씩 입력하세요.";
        } catch (error) {
            if (token === generation && !removed) status.textContent = `미리보기를 불러오지 못했습니다. ${error.message}`;
        }
    }
    const schedule = () => { clearTimeout(timer); timer = setTimeout(refresh, 350); };
    root.querySelector("button").onclick = refresh;
    watch(node, ["reference_image_paths", "include_grid_reference"], schedule);
    chain(node, "onRemoved", () => { removed = true; generation++; clearTimeout(timer); });
    schedule();
}
const gcd = (a, b) => b ? gcd(b, a % b) : a;
const ratio = (a, b) => { const d = gcd(a, b); return `${a / d}:${b / d}`; };
function gridPreview(node) {
    const root = panel(node, "layout_preview", 395);
    root.innerHTML = `<div class="sg-kicker">LIVE BOARD LAYOUT</div><div class="sg-presets"><button data-ratio="16,9">가로 컷 16:9</button><button data-ratio="9,16">세로 컷 9:16</button><button data-ratio="1,1">정사각 컷</button></div><div class="sg-board-wrap"><div class="sg-board"></div></div><div class="sg-stats"><div class="sg-stat"><span class="sg-muted">레이아웃 기준</span><b class="sg-sheet"></b><span class="sg-muted sg-sheet-size"></span></div><div class="sg-stat"><span class="sg-muted">컷 비율</span><b class="sg-shot"></b><span class="sg-muted sg-shot-size"></span></div></div><div class="sg-note"></div>`;
    const board = root.querySelector(".sg-board");
    const note = root.querySelector(".sg-note");
    function render() {
        const rows = Math.max(1, Math.round(Number(value(node, "rows", 3))));
        const columns = Math.max(1, Math.round(Number(value(node, "columns", 4))));
        const width = Math.max(1, Math.round(Number(value(node, "width", 1920))));
        const height = Math.max(1, Math.round(Number(value(node, "height", 1080))));
        board.style.gridTemplateColumns = `repeat(${columns},1fr)`;
        board.style.gridTemplateRows = `repeat(${rows},1fr)`;
        const maxWidth = Math.max(100, (node.size?.[0] || 500) - 70);
        const scale = Math.min(maxWidth / width, 152 / height);
        board.style.width = `${Math.round(width * scale)}px`;
        board.style.height = `${Math.round(height * scale)}px`;
        board.replaceChildren();
        for (let i = 0; i < Math.min(rows * columns, 1024); i++) {
            const cell = document.createElement("div"); cell.className = "sg-cell";
            cell.textContent = String(i + 1).padStart(2, "0"); board.append(cell);
        }
        root.querySelector(".sg-sheet").textContent = `${ratio(width, height)} · ${rows}행 × ${columns}열`;
        root.querySelector(".sg-shot").textContent = `${ratio(width * rows, height * columns)} · ${rows * columns}컷`;
        root.querySelector(".sg-sheet-size").textContent = `${width} × ${height} px`;
        root.querySelector(".sg-shot-size").textContent = `${+(width / columns).toFixed(1)} × ${+(height / rows).toFixed(1)} px`;
        note.textContent = "레이아웃 기준 크기입니다. 생성·저장 해상도는 모델 / 해상도 칸에서 선택하세요.";
        node.setDirtyCanvas?.(true, true);
    }
    function preset(a, b) {
        const rows = Number(value(node, "rows", 3));
        const columns = Number(value(node, "columns", 4));
        const unitW = columns * a, unitH = rows * b;
        let best = null;
        for (let n = 1; n * Math.max(unitW, unitH) <= 3840; n++) {
            const w = unitW * n, h = unitH * n;
            if (w < 1024 || h < 1024 || w % 16 || h % 16 || w * h > 8294400 || Math.max(w / h, h / w) > 3) continue;
            const score = Math.abs(Math.max(w, h) - 2304);
            if (!best || score < best.score) best = { w, h, score };
        }
        if (!best) { note.textContent = "이 행·열 조합에서는 지원 크기를 만들 수 없습니다. 행·열 수를 줄여주세요."; return; }
        for (const [name, next] of [["width", best.w], ["height", best.h]]) {
            const w = widget(node, name); w.value = next; w.callback?.(next);
        }
        render();
        app.graph?.change?.();
    }
    for (const button of root.querySelectorAll("button[data-ratio]")) {
        button.onclick = () => preset(...button.dataset.ratio.split(",").map(Number));
    }
    watch(node, ["rows", "columns", "width", "height"], render);
    chain(node, "onResize", render);
    render();
}
app.registerExtension({
    name: "StoryGrid.AssetAndLayoutPreview",
    loadedGraphNode(node) {
        stylePresetButtons(node);
    },
    afterConfigureGraph() {
        const nodes = app.graph?._nodes || [];
        if (!nodes.some(node => node.type === "StoryGridResolution")) return;
        const style = nodes.find(node => Number(node.id) === 31 && node.type === "PrimitiveStringMultiline" && /^STYLE\b/.test(node.title));
        if (style) {
            style.properties.story_grid_style_presets = true;
            stylePresetButtons(style);
        }
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "StoryGridReferenceBatch") chain(nodeType.prototype, "onNodeCreated", function () { referenceGallery(this); });
        if (nodeData.name === "StoryGridReference") chain(nodeType.prototype, "onNodeCreated", function () { gridPreview(this); });
    },
});
