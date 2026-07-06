document.addEventListener("DOMContentLoaded", function () {
    // Generic Search Logic
    const searchInputs = document.querySelectorAll('.generic-search-input');
    
    searchInputs.forEach(function(searchInput) {
        searchInput.addEventListener('input', function () {
            const query = this.value.toLowerCase().trim();
            const targetSelector = this.getAttribute('data-target');
            if (!targetSelector) return;
            
            const targetItems = document.querySelectorAll(targetSelector);

            targetItems.forEach(function (item) {
                // If it's a table row with specific search-text cells
                const searchCells = item.querySelectorAll('.search-text');
                let textToSearch = '';
                
                if (searchCells.length > 0) {
                    searchCells.forEach(cell => textToSearch += cell.textContent.toLowerCase() + ' ');
                } else {
                    // Fallback to textContent of the whole item (useful for cards and generic rows)
                    textToSearch = item.textContent.toLowerCase();
                }

                if (textToSearch.includes(query)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
});