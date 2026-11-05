var tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    var player;
function openPopup() {
  document.getElementById("imgPopup").style.display = "flex";
}

function closePopup() {
  document.getElementById("imgPopup").style.display = "none";
}
// img 2
function openPopup2() {
  document.getElementById("imgPopup2").style.display = "flex";
}

function closePopup2() {
  document.getElementById("imgPopup2").style.display = "none";
}
// img 3
// YouTube Iframe API script
    

    // YouTube player object
    var player;

    // img 3
    function openPopup3() {
        document.getElementById("imgPopup3").style.display = "flex";
        // Create YouTube player if not already created
        if (!player) {
            player = new YT.Player('youtubePlayer3', {
                height: '360',
                width: '640',
                videoId: 'zqKMlf66IP8',
                events: {
                    'onReady': onPlayerReady
                }
            });
        } else {
            // If the player is already created, cue and play the video from the start
            player.seekTo(0);
            player.playVideo();
        }
    }

    function closePopup3() {
        document.getElementById("imgPopup3").style.display = "none";
        // Pause the video when closing the popup
        if (player) {
            player.pauseVideo();
        }
    }

    // Callback function when the YouTube player is ready
    function onPlayerReady(event) {
        // You can perform additional actions when the player is ready
        // Play the video automatically when the popup is opened
        player.playVideo();
    }
// img 4
function openPopup4() {
  document.getElementById("imgPopup4").style.display = "flex";
}

function closePopup4() {
  document.getElementById("imgPopup4").style.display = "none";
}
// img 5
function openPopup5() {
  document.getElementById("imgPopup5").style.display = "flex";
}

function closePopup5() {
  document.getElementById("imgPopup5").style.display = "none";
}
// img 6
function openPopup6() {
  document.getElementById("imgPopup6").style.display = "flex";
}

function closePopup6() {
  document.getElementById("imgPopup6").style.display = "none";
}
// img 7
function openPopup7() {
  document.getElementById("imgPopup7").style.display = "flex";
}

function closePopup7() {
  document.getElementById("imgPopup7").style.display = "none";
}
// img 8
function openPopup8() {
  document.getElementById("imgPopup8").style.display = "flex";
}

function closePopup8() {
  document.getElementById("imgPopup8").style.display = "none";
}
// img 8
function openPopup9() {
  document.getElementById("imgPopup9").style.display = "flex";
}

function closePopup9() {
  document.getElementById("imgPopup9").style.display = "none";
}
// img 10
function openPopup10() {
  document.getElementById("imgPopup10").style.display = "flex";
}

function closePopup10() {
  document.getElementById("imgPopup10").style.display = "none";
}
// img 10
function openPopup11() {
  document.getElementById("imgPopup11").style.display = "flex";
}

function closePopup11() {
  document.getElementById("imgPopup11").style.display = "none";
}
// img 12
function openPopup12() {
  document.getElementById("imgPopup12").style.display = "flex";
}

function closePopup12() {
  document.getElementById("imgPopup12").style.display = "none";
}