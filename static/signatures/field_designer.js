(function () {
  const pageSizes = JSON.parse(document.getElementById("page-sizes-data").textContent);
  const initialFields = JSON.parse(document.getElementById("fields-data").textContent || "[]");
  const image = document.getElementById("pdf-page-image");
  const layer = document.getElementById("field-layer");
  const stage = document.getElementById("designer-stage");
  const pageLabel = document.getElementById("page-label");
  const fieldsInput = document.getElementById("fields-json");
  const fieldList = document.getElementById("field-list");
  const form = document.getElementById("designer-form");
  const pageImageBaseUrl = window.fieldDesignerConfig.pageImageBaseUrl;

  let page = 1;
  let activeType = "signature";
  let fields = initialFields || [];
  let drawing = null;
  let moving = null;
  let resizing = null;
  let selectedIndex = -1;
  let suppressNextClick = false;
  let zoom = 1;

  function pageSize() {
    return pageSizes[page - 1];
  }

  function imageRect() {
    return image.getBoundingClientRect();
  }

  function pointFromEvent(event) {
    const rect = imageRect();
    return {
      x: Math.max(0, Math.min(rect.width, event.clientX - rect.left)),
      y: Math.max(0, Math.min(rect.height, event.clientY - rect.top)),
    };
  }

  function screenToPdf(box) {
    const size = pageSize();
    const rect = imageRect();
    const x = (box.left / rect.width) * size.width;
    const y = size.height - ((box.top + box.height) / rect.height) * size.height;
    const w = (box.width / rect.width) * size.width;
    const h = (box.height / rect.height) * size.height;
    return { x, y, w, h };
  }

  function pdfToScreen(field) {
    const size = pageSizes[field.page - 1];
    const rect = imageRect();
    return {
      left: (field.x / size.width) * rect.width,
      top: ((size.height - field.y - field.h) / size.height) * rect.height,
      width: (field.w / size.width) * rect.width,
      height: (field.h / size.height) * rect.height,
    };
  }

  function normalizeBox(start, end) {
    const left = Math.min(start.x, end.x);
    const top = Math.min(start.y, end.y);
    return {
      left,
      top,
      width: Math.abs(end.x - start.x),
      height: Math.abs(end.y - start.y),
    };
  }

  function labelFor(type) {
    if (type === "signature") return "Signature";
    if (type === "initial") return "Initial";
    if (type === "name") return "Printed Name";
    if (type === "date") return "Date";
    return type;
  }

  function defaultSizeFor(type) {
    if (type === "signature") return { width: 180, height: 48 };
    if (type === "initial") return { width: 80, height: 28 };
    if (type === "name") return { width: 180, height: 24 };
    if (type === "date") return { width: 120, height: 24 };
    return { width: 140, height: 32 };
  }

  function placeDefaultField(type, point) {
    if (!image.complete || !imageRect().width || !pageSize()) return;
    const size = defaultSizeFor(type);
    const rect = imageRect();
    const box = {
      left: Math.max(0, Math.min(rect.width - size.width, point.x - size.width / 2)),
      top: Math.max(0, Math.min(rect.height - size.height, point.y - size.height / 2)),
      width: size.width,
      height: size.height,
    };
    fields.push({
      type,
      page,
      label: labelFor(type),
      ...screenToPdf(box),
    });
    selectedIndex = fields.length - 1;
    renderFields();
  }

  function setBoxStyle(element, box) {
    element.style.left = `${box.left}px`;
    element.style.top = `${box.top}px`;
    element.style.width = `${box.width}px`;
    element.style.height = `${box.height}px`;
  }

  function screenBoxToField(index, box) {
    const pdfBox = screenToPdf(box);
    fields[index] = {
      ...fields[index],
      x: pdfBox.x,
      y: pdfBox.y,
      w: pdfBox.w,
      h: pdfBox.h,
    };
  }

  function renderFields() {
    layer.innerHTML = "";
    fields.forEach((field, index) => {
      if (field.page !== page) return;
      const box = document.createElement("button");
      box.type = "button";
      box.className = `placed-field ${field.type}`;
      if (index === selectedIndex) box.classList.add("selected");
      box.textContent = labelFor(field.type);
      box.dataset.index = index;
      setBoxStyle(box, pdfToScreen(field));
      box.addEventListener("click", function (event) {
        event.stopPropagation();
        selectedIndex = index;
        renderFields();
      });
      box.addEventListener("mousedown", function (event) {
        event.stopPropagation();
        event.preventDefault();
        selectedIndex = index;
        const currentBox = pdfToScreen(fields[index]);
        moving = {
          index,
          start: pointFromEvent(event),
          box: currentBox,
        };
        renderFields();
      });
      ["nw", "ne", "sw", "se"].forEach((corner) => {
        const handle = document.createElement("span");
        handle.className = `resize-handle ${corner}`;
        handle.addEventListener("mousedown", function (event) {
          event.stopPropagation();
          event.preventDefault();
          selectedIndex = index;
          resizing = {
            index,
            corner,
            start: pointFromEvent(event),
            box: pdfToScreen(fields[index]),
          };
          renderFields();
        });
        box.appendChild(handle);
      });
      layer.appendChild(box);
    });
    renderFieldList();
    fieldsInput.value = JSON.stringify(fields);
  }

  function renderFieldList() {
    if (!fields.length) {
      fieldList.innerHTML = "<p class=\"muted\">No fields placed yet.</p>";
      return;
    }
    fieldList.innerHTML = "";
    fields.forEach((field, index) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "field-list-item";
      if (index === selectedIndex) item.classList.add("selected");
      item.textContent = `${labelFor(field.type)} - page ${field.page}`;
      item.addEventListener("click", function () {
        page = field.page;
        selectedIndex = index;
        loadPage();
      });
      fieldList.appendChild(item);
    });
  }

  function loadPage() {
    pageLabel.textContent = `Page ${page} of ${pageSizes.length}`;
    image.src = `${pageImageBaseUrl}${page}.png`;
  }

  function applyZoom() {
    if (!image.naturalWidth) return;
    image.style.width = `${Math.round(image.naturalWidth * zoom)}px`;
    image.style.height = "auto";
    renderFields();
  }

  function fitPage() {
    if (!image.naturalWidth || !image.naturalHeight) return;
    const stageTop = stage.getBoundingClientRect().top;
    const availableWidth = Math.max(360, stage.clientWidth - 28);
    const availableHeight = Math.max(520, window.innerHeight - stageTop - 28);
    const fitWidthZoom = availableWidth / image.naturalWidth;
    const fitHeightZoom = availableHeight / image.naturalHeight;
    zoom = Math.min(fitWidthZoom, fitHeightZoom) * 1.14;
    zoom = Math.max(0.35, Math.min(1.45, zoom));
    applyZoom();
  }

  document.querySelectorAll(".tool-button").forEach((button) => {
    button.addEventListener("click", function () {
      activeType = button.dataset.fieldType;
      document.querySelectorAll(".tool-button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      placeDefaultField(activeType, {
        x: imageRect().width / 2,
        y: imageRect().height / 2,
      });
    });

    button.addEventListener("dragstart", function (event) {
      activeType = button.dataset.fieldType;
      event.dataTransfer.setData("text/plain", activeType);
      event.dataTransfer.effectAllowed = "copy";
      document.querySelectorAll(".tool-button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });

  document.getElementById("prev-page").addEventListener("click", function () {
    if (page > 1) {
      page -= 1;
      selectedIndex = -1;
      loadPage();
    }
  });

  document.getElementById("next-page").addEventListener("click", function () {
    if (page < pageSizes.length) {
      page += 1;
      selectedIndex = -1;
      loadPage();
    }
  });

  document.getElementById("zoom-out").addEventListener("click", function () {
    zoom = Math.max(0.25, zoom - 0.1);
    applyZoom();
  });

  document.getElementById("zoom-fit").addEventListener("click", fitPage);

  document.getElementById("zoom-in").addEventListener("click", function () {
    zoom = Math.min(1.8, zoom + 0.1);
    applyZoom();
  });

  stage.addEventListener("mousedown", function (event) {
    if (event.target !== image && event.target !== layer && event.target !== stage) return;
    const start = pointFromEvent(event);
    const preview = document.createElement("div");
    preview.className = `placed-field drawing ${activeType}`;
    preview.textContent = labelFor(activeType);
    layer.appendChild(preview);
    drawing = { start, preview };
  });

  function allowDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = "copy";
  }

  function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    const droppedType = event.dataTransfer.getData("text/plain") || activeType;
    if (!["signature", "initial", "name", "date"].includes(droppedType)) return;
    placeDefaultField(droppedType, pointFromEvent(event));
  }

  [stage, image, layer].forEach((target) => {
    target.addEventListener("dragenter", allowDrop);
    target.addEventListener("dragover", allowDrop);
    target.addEventListener("drop", handleDrop);
  });

  window.addEventListener("mousemove", function (event) {
    if (drawing) {
      const current = pointFromEvent(event);
      setBoxStyle(drawing.preview, normalizeBox(drawing.start, current));
      return;
    }
    if (moving) {
      const current = pointFromEvent(event);
      const rect = imageRect();
      const dx = current.x - moving.start.x;
      const dy = current.y - moving.start.y;
      const nextBox = {
        ...moving.box,
        left: Math.max(0, Math.min(rect.width - moving.box.width, moving.box.left + dx)),
        top: Math.max(0, Math.min(rect.height - moving.box.height, moving.box.top + dy)),
      };
      screenBoxToField(moving.index, nextBox);
      renderFields();
      return;
    }
    if (resizing) {
      const current = pointFromEvent(event);
      const rect = imageRect();
      let left = resizing.box.left;
      let top = resizing.box.top;
      let right = resizing.box.left + resizing.box.width;
      let bottom = resizing.box.top + resizing.box.height;
      if (resizing.corner.includes("w")) left = current.x;
      if (resizing.corner.includes("e")) right = current.x;
      if (resizing.corner.includes("n")) top = current.y;
      if (resizing.corner.includes("s")) bottom = current.y;
      left = Math.max(0, Math.min(rect.width, left));
      right = Math.max(0, Math.min(rect.width, right));
      top = Math.max(0, Math.min(rect.height, top));
      bottom = Math.max(0, Math.min(rect.height, bottom));
      const nextBox = {
        left: Math.min(left, right),
        top: Math.min(top, bottom),
        width: Math.max(16, Math.abs(right - left)),
        height: Math.max(16, Math.abs(bottom - top)),
      };
      screenBoxToField(resizing.index, nextBox);
      renderFields();
    }
  });

  window.addEventListener("mouseup", function (event) {
    if (moving || resizing) {
      moving = null;
      resizing = null;
      suppressNextClick = true;
      return;
    }
    if (!drawing) return;
    const current = pointFromEvent(event);
    const box = normalizeBox(drawing.start, current);
    drawing.preview.remove();
    drawing = null;
    if (box.width < 16 || box.height < 16) {
      placeDefaultField(activeType, current);
      suppressNextClick = true;
      return;
    }
    fields.push({
      type: activeType,
      page,
      label: labelFor(activeType),
      ...screenToPdf(box),
    });
    selectedIndex = fields.length - 1;
    renderFields();
    suppressNextClick = true;
  });

  window.addEventListener("keydown", function (event) {
    if ((event.key === "Delete" || event.key === "Backspace") && selectedIndex >= 0) {
      fields.splice(selectedIndex, 1);
      selectedIndex = -1;
      renderFields();
    }
  });

  image.addEventListener("load", function () {
    requestAnimationFrame(fitPage);
  });

  window.addEventListener("resize", function () {
    requestAnimationFrame(fitPage);
  });
  image.addEventListener("click", function (event) {
    if (drawing || suppressNextClick) {
      suppressNextClick = false;
      return;
    }
    placeDefaultField(activeType, pointFromEvent(event));
  });

  form.addEventListener("submit", function (event) {
    fieldsInput.value = JSON.stringify(fields);
    if (!fields.length) {
      event.preventDefault();
      alert("Place at least one field before sending.");
    }
  });

  loadPage();
})();
