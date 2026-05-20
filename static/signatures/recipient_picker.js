(function () {
  const select = document.getElementById("id_recipients");
  if (!select) return;

  const form = select.closest("form");
  if (form) {
    form.setAttribute("autocomplete", "off");
  }

  const choices = Array.from(select.options).map((option) => ({
    id: option.value,
    label: option.textContent,
    selected: option.hasAttribute("selected"),
  }));

  const wrapper = document.createElement("div");
  wrapper.className = "recipient-picker";
  wrapper.innerHTML = `
    <div class="recipient-column">
      <div class="recipient-column-header">
        <strong>Available Customers</strong>
        <input type="search" class="recipient-search" placeholder="Search customers">
      </div>
      <div class="recipient-list available-list"></div>
    </div>
    <div class="recipient-actions">
      <button type="button" class="add-selected">Add</button>
      <button type="button" class="add-all">Add all</button>
      <button type="button" class="remove-selected">Remove</button>
      <button type="button" class="remove-all">Clear all</button>
    </div>
    <div class="recipient-column">
      <div class="recipient-column-header">
        <strong>Selected Recipients</strong>
        <span class="recipient-count">0</span>
      </div>
      <div class="recipient-list selected-list"></div>
    </div>
  `;

  select.parentNode.insertBefore(wrapper, select.nextSibling);

  const availableList = wrapper.querySelector(".available-list");
  const selectedList = wrapper.querySelector(".selected-list");
  const searchInput = wrapper.querySelector(".recipient-search");
  const countLabel = wrapper.querySelector(".recipient-count");
  const selectedIds = new Set(choices.filter((choice) => choice.selected).map((choice) => choice.id));
  Array.from(select.options).forEach((option) => {
    option.selected = selectedIds.has(option.value);
  });

  function render() {
    const query = searchInput.value.trim().toLowerCase();
    availableList.innerHTML = "";
    selectedList.innerHTML = "";

    choices
      .filter((choice) => !selectedIds.has(choice.id))
      .filter((choice) => !query || choice.label.toLowerCase().includes(query))
      .forEach((choice) => availableList.appendChild(createItem(choice, "available")));

    choices
      .filter((choice) => selectedIds.has(choice.id))
      .forEach((choice) => selectedList.appendChild(createItem(choice, "selected")));

    Array.from(select.options).forEach((option) => {
      option.selected = selectedIds.has(option.value);
    });
    countLabel.textContent = `${selectedIds.size} selected`;
  }

  function createItem(choice, mode) {
    const label = document.createElement("label");
    label.className = "recipient-item";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = choice.id;
    checkbox.dataset.mode = mode;
    const span = document.createElement("span");
    span.textContent = choice.label;
    label.appendChild(checkbox);
    label.appendChild(span);
    label.addEventListener("dblclick", function () {
      if (mode === "available") {
        selectedIds.add(choice.id);
      } else {
        selectedIds.delete(choice.id);
      }
      render();
    });
    return label;
  }

  function checkedIds(mode) {
    return Array.from(wrapper.querySelectorAll(`input[data-mode="${mode}"]:checked`)).map((item) => item.value);
  }

  wrapper.querySelector(".add-selected").addEventListener("click", function () {
    checkedIds("available").forEach((id) => selectedIds.add(id));
    render();
  });

  wrapper.querySelector(".add-all").addEventListener("click", function () {
    choices.forEach((choice) => selectedIds.add(choice.id));
    render();
  });

  wrapper.querySelector(".remove-selected").addEventListener("click", function () {
    checkedIds("selected").forEach((id) => selectedIds.delete(id));
    render();
  });

  wrapper.querySelector(".remove-all").addEventListener("click", function () {
    selectedIds.clear();
    render();
  });

  searchInput.addEventListener("input", render);
  render();
})();
