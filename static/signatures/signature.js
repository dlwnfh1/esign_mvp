(function () {
  const canvas = document.getElementById("signature-pad");
  const input = document.getElementById("id_signature_data");
  const clearButton = document.getElementById("clear-signature");
  const form = document.getElementById("sign-form");
  if (!canvas || !input || !form) return;

  const ctx = canvas.getContext("2d");
  let drawing = false;
  let hasInk = false;

  function resizeCanvas() {
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * ratio;
    canvas.height = rect.height * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#111";
  }

  function point(event) {
    const rect = canvas.getBoundingClientRect();
    const source = event.touches ? event.touches[0] : event;
    return {
      x: source.clientX - rect.left,
      y: source.clientY - rect.top,
    };
  }

  function start(event) {
    event.preventDefault();
    drawing = true;
    const p = point(event);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  }

  function move(event) {
    if (!drawing) return;
    event.preventDefault();
    const p = point(event);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    hasInk = true;
  }

  function stop() {
    drawing = false;
  }

  function clear() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    input.value = "";
    hasInk = false;
  }

  window.addEventListener("resize", resizeCanvas);
  canvas.addEventListener("mousedown", start);
  canvas.addEventListener("mousemove", move);
  window.addEventListener("mouseup", stop);
  canvas.addEventListener("touchstart", start, { passive: false });
  canvas.addEventListener("touchmove", move, { passive: false });
  canvas.addEventListener("touchend", stop);
  clearButton.addEventListener("click", clear);

  form.addEventListener("submit", function (event) {
    if (!hasInk) {
      event.preventDefault();
      alert("Please draw your signature before submitting.");
      return;
    }
    input.value = canvas.toDataURL("image/png");
  });

  resizeCanvas();
})();
