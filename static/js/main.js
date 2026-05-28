// Global scripts for the entire website

// Fix bfcache issue (back/forward)
window.addEventListener("pageshow", function(event) {
    console.log("pageshow fired, persisted:", event.persisted);
    if (event.persisted) {
        // Force reload
        document.body.style.visibility = "hidden";
        location.reload();
    }
});