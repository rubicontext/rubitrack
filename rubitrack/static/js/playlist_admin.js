/* Playlist admin favourite star toggle functionality */
(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Handle star click
        $(document).on('click', '.favourite-star', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            var $star = $(this);
            var playlistId = $star.data('playlist-id');
            
            if (!playlistId) {
                console.error('No playlist ID found');
                return;
            }
            
            // Get CSRF token
            var csrftoken = getCookie('csrftoken');
            
            // Send AJAX request
            $.ajax({
                url: '/track/toggle_playlist_favourite/',
                type: 'POST',
                data: {
                    'playlist_id': playlistId,
                    'csrfmiddlewaretoken': csrftoken
                },
                success: function(response) {
                    if (response.success) {
                        // Toggle star appearance
                        var isFavourite = response.is_favourite;
                        
                        if (isFavourite) {
                            $star.text('★');
                            $star.removeClass('favourite-star-empty');
                            $star.addClass('favourite-star-filled');
                            $star.css('color', '#FFD700');
                        } else {
                            $star.text('☆');
                            $star.removeClass('favourite-star-filled');
                            $star.addClass('favourite-star-empty');
                            $star.css('color', '#ccc');
                        }
                        
                        console.log('Playlist favourite toggled:', response);
                    } else {
                        alert('Error toggling favourite: ' + (response.error || 'Unknown error'));
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX error:', status, error);
                    alert('Error toggling favourite playlist');
                }
            });
        });
    });
    
    // Helper function to get CSRF token from cookies
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
})(django.jQuery);
