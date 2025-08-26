// main.js - global JS for stybase

document.addEventListener("DOMContentLoaded", () => {
    
    // ---------------- Flash Message Auto-Dismiss ----------------
    const flashMessages = document.querySelectorAll(".alert-dismissible");
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.classList.remove("show");
            msg.classList.add("hide");
            // Remove element after fade out (optional)
            setTimeout(() => msg.remove(), 500);
        }, 5000); // auto-dismiss after 5 seconds
    });

    // ---------------- Navbar Search Toggle ----------------
    const searchToggle = document.getElementById("searchToggle");
    if (searchToggle) {
        searchToggle.addEventListener("click", () => {
            const searchInput = document.getElementById("searchInput");
            if (searchInput) {
                searchInput.classList.toggle("d-none");
                if (!searchInput.classList.contains("d-none")) {
                    searchInput.focus();
                }
            }
        });
    }

    // ---------------- Simple Form Validation ----------------
    const forms = document.querySelectorAll("form.needs-validation");
    forms.forEach(form => {
        form.addEventListener("submit", (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });

    // ---------------- Developer-Specific UI Logic ----------------
    // Example: hide/show register app section based on account type
    const accountType = document.body.dataset.role; // set <body data-role="{{ role }}">
    const devSection = document.getElementById("developer-section");
    if (devSection && accountType !== "developer") {
        devSection.style.display = "none";
    }

});
