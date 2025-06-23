// lnmt/static/js/theme.js

document.addEventListener("DOMContentLoaded", function() {
  let themeSelect = document.getElementById("theme-select");
  if (themeSelect) {
    themeSelect.addEventListener("change", function() {
      fetch("/api/user/theme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: this.value })
      })
      .then(resp => resp.json())
      .then(data => {
        if (data.success) {
          location.reload();
        }
      });
    });
  }
});
