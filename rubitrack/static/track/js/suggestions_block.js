document.addEventListener('DOMContentLoaded', function() {
    const suggestionsBlock = document.getElementById('suggestions-block');
    if (!suggestionsBlock) return;
    
    const bpmSlider = document.getElementById('bpm-range-slider');
    const bpmValue = document.getElementById('bpm-range-value');
    const genreRadios = document.querySelectorAll('input[name="genre-mode"]');
    const suggestionsCount = document.getElementById('suggestions-count');
    const sortableHeaders = document.querySelectorAll('.sortable');
    
    let currentSort = { field: 'title', order: 'asc' };
    const currentTrackId = suggestionsBlock.dataset.trackId;
    const ajaxUrl = suggestionsBlock.dataset.ajaxUrl;
    
    // Mise à jour de la valeur du slider BPM
    if (bpmSlider && bpmValue) {
        bpmSlider.addEventListener('input', function() {
            bpmValue.textContent = this.value;
            updateSuggestions();
        });
    }
    
    // Gestion des radio buttons genre
    genreRadios.forEach(radio => {
        radio.addEventListener('change', updateSuggestions);
    });
    
    // Gestion du tri des colonnes
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const field = this.dataset.sort;
            
            // Inverser l'ordre si on clique sur la même colonne
            if (currentSort.field === field) {
                currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.order = 'asc';
            }
            
            updateSortIndicators();
            updateSuggestions();
        });
    });
    
    function updateSortIndicators() {
        // Réinitialiser tous les indicateurs
        document.querySelectorAll('.sort-indicator').forEach(indicator => {
            indicator.className = 'sort-indicator';
        });
        
        // Mettre à jour l'indicateur actuel
        const activeIndicator = document.querySelector(`[data-field="${currentSort.field}"]`);
        if (activeIndicator) {
            activeIndicator.className = `sort-indicator ${currentSort.order}`;
        }
    }
    
    function updateSuggestions() {
        if (!currentTrackId || !ajaxUrl) return;
        
        const bpmRange = bpmSlider ? parseInt(bpmSlider.value) : 10;
        const genreMode = document.querySelector('input[name="genre-mode"]:checked')?.value || 'exact';
        
        const requestData = {
            track_id: parseInt(currentTrackId),
            bpm_range: bpmRange,
            genre_mode: genreMode,
            sort_by: currentSort.field,
            sort_order: currentSort.order
        };
        
        fetch(ajaxUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            updateSuggestionsTable(data.suggestions);
            if (suggestionsCount) {
                suggestionsCount.textContent = data.count;
            }
        })
        .catch(error => {
            console.error('Erreur lors de la récupération des suggestions:', error);
        });
    }
    
    function updateSuggestionsTable(suggestions) {
        const tbody = document.getElementById('suggestions-tbody');
        if (!tbody) return;
        
        if (suggestions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-suggestions">Aucune suggestion trouvée</td></tr>';
            return;
        }
        
        tbody.innerHTML = suggestions.map(suggestion => `
            <tr class="suggestion-row" data-track-id="${suggestion.id}">
                <td class="track-title">${escapeHtml(suggestion.title)}</td>
                <td class="track-artist">
                    <span class="artist_green_flashy">${escapeHtml(suggestion.artist)}</span>
                </td>
                <td class="track-bpm">${suggestion.bpm || '--'}</td>
                <td class="track-key">${escapeHtml(suggestion.musical_key) || '--'}</td>
                <td class="track-ranking">
                    ${suggestion.ranking ? 
                        '★'.repeat(suggestion.ranking) + '☆'.repeat(5 - suggestion.ranking) : 
                        '--'
                    }
                </td>
            </tr>
        `).join('');
        
        // Ajouter les événements de clic sur les nouvelles lignes
        tbody.querySelectorAll('.suggestion-row').forEach(row => {
            row.addEventListener('click', function() {
                const trackId = this.dataset.trackId;
                handleTrackSelection(trackId);
            });
        });
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }
    
    function handleTrackSelection(trackId) {
        // Action à effectuer lors de la sélection d'une track
        console.log('Track sélectionnée:', trackId);
        // Ici vous pouvez ajouter l'action souhaitée (redirection, modal, etc.)
    }
    
    // Initialiser les indicateurs de tri
    updateSortIndicators();
});
