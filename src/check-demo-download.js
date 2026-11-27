(() => {
    const form = document.querySelector("[data-demo-check]");
    const manual = document.querySelector("#manual-check");
    const fallback = document.querySelector("[data-demo-check-fallback]");
    fallback.querySelector("a").addEventListener("click", () => {
        manual.open = true;
    });

    if (!globalThis.crypto?.subtle || !Blob.prototype.arrayBuffer) return;

    const reference = form.querySelector("select");
    const localFile = form.querySelector('input[type="file"]');
    const button = form.querySelector("button");
    const status = form.querySelector('[role="status"]');
    const fingerprints = form.querySelector("dl");
    const download = form.querySelector("[data-official-download]");
    const edition = form.querySelector("[data-demo-edition]");

    function updateSelection() {
        status.textContent = "";
        fingerprints.hidden = true;
        if (download) download.hidden = true;
        if (edition) {
            edition.textContent = reference.selectedOptions[0]?.closest("optgroup")?.label || "";
            edition.hidden = !edition.textContent;
        }
        button.disabled = !reference.value || !localFile.files.length;
    }

    form.addEventListener("change", updateSelection);
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (button.disabled) return;

        const file = localFile.files[0];
        const published = reference.selectedOptions[0].dataset;
        const expected = published.sha256;
        button.disabled = reference.disabled = localFile.disabled = true;
        fingerprints.hidden = true;
        if (download) download.hidden = true;
        status.textContent = form.dataset.working;

        try {
            const bytes = await file.arrayBuffer();
            const digest = await crypto.subtle.digest("SHA-256", bytes);
            const actual = Array.from(new Uint8Array(digest), (byte) =>
                byte.toString(16).padStart(2, "0")
            ).join("");
            fingerprints.querySelector("[data-expected]").textContent = expected;
            fingerprints.querySelector("[data-actual]").textContent = actual;
            fingerprints.hidden = false;
            const matches = actual === expected;
            status.textContent = matches ? form.dataset.match : form.dataset.mismatch;
            if (!matches && download && published.download) {
                download.href = published.download;
                download.hidden = false;
            }
        } catch {
            status.textContent = form.dataset.error;
        } finally {
            button.disabled = reference.disabled = localFile.disabled = false;
        }
    });

    updateSelection();
    form.hidden = false;
    fallback.hidden = true;
})();
