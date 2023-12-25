<?php
    define('APP_VERSION', '23.11.29'); // You can replace '1.0.0' with your desired version number
    session_id("regattastart");
    session_start();
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    ini_set('display_errors', 1); 
    error_reporting(E_ALL);
?>
<!-- Your HTML to display data from the session -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <! -- meta http-equiv="refresh" content="200" -->
    <title>Regattastart</title>
    <! -- JavaScript to dynamically add a placeholder text or an image to the page when -->
    <! -- there are no pictures available yet. -->
    <script>
        function showPlaceholder() {
            var imageContainer = document.getElementById('image-container');
            var images = imageContainer.getElementsByTagName('img');
            var placeholderText = 'Pictures pending until 5 minutes before start';

            // Check if there are images and if all images have loaded
            if (images.length > 0 && Array.from(images).every(img => img.complete)) {
                // Remove any existing placeholder text
                while (imageContainer.firstChild) {
                    imageContainer.removeChild(imageContainer.firstChild);
                }
            } else {
                // Add a placeholder text
                var textNode = document.createTextNode(placeholderText);
                imageContainer.appendChild(textNode);
            }
        }
    </script>
    <style>
    img {
        max-width: 100%;
        height: auto;
    }
    </style>
    <style>
    video {
        max-width: 100%;
        height: auto;
    }
    </style>
    <link rel="stylesheet" href="/w3.css">
</head>
<?php
    // Retrieve and display data from the session
    if (isset($_SESSION["form_data"])) {
        $form_data = $_SESSION["form_data"];
        // Display the data or do whatever you need
        echo "     Start time: " . $form_data['start_time'];
        echo ", Video Delay: " . $form_data['video_delay'];
        echo ", Video Duration: " . $form_data['video_dur']; 
        
        $num_video = $form_data['num_video'];
        echo ", Number of Videos: " . $num_video;

        $num_starts = $form_data['num_starts'];
        echo ", Number of starts: " . $num_starts;
    }
?>  

<?php
    // Retrieve and display data from the session

    if (isset($_SESSION["form_data"])){
        $form_data = $_SESSION['form_data'];
        $num_starts= $form_data['num_starts'];
        echo ", Number of starts: " . $num_starts; 
    }

    if (isset($_SESSION['video_end'])){
        $video_end = $_SESSION['video_end'];
        echo ", Max duration from start: " . $video_end; 
    }
    if (isset($_SESSION["start_time"])){
        $start_time= $_SESSION['start_time'];
        $start_time= $_form_data['start_time'];
        echo ", First start time: " . $start_time; 
    }

    if (isset($_SESSION['video_dur'])){
        $video_dur = $_SESSION['video_dur'];
        $video_dur = $_form_data['video_dur'];
        echo ", Video Duration: " . $video_dur; 
    
        $video_delay = $SESSION['video_delay'];
        $video_delay = $form_data['video_delay'];
        echo ", Video Delay: " . $video_delay;

        $num_video = $SESSION['num_video'];
        $num_video = $form_data['num_video'];
        echo ", Number of Videos: " . $num_video;
    }
?>
<header>
<div align="center">
    <div class="w3-panel w3-blue">
        <h2> Regattastart  </h2>
    </div>
</div>
<!-- Here is our main header that is used across all the pages of our website -->
 <meta http-equiv="refresh" content="200" >
</header>
<body onload="showPlaceholder()">
    <div align="center">
    <?php 
        echo "     Version: " . APP_VERSION . "<br><p></p>"; 
    ?>
    </div>
    <div align="center">
        <div id="image-container">
            <!-- Your image elements will be added here dynamically -->
        </div>
    </div>
    <!-- Here is our page's main content -->
    <main>
    <div align="center">
    <h4><a href="/index6.php" title="Merged 1 and 2 start versions together"> Setup Page Regattastart6 </a></h4>
    <div align="center">
    <div align="center">
    <h4><a href="/index9.php" title="New with image detection"> Setup page Regattastart8 </a></h4>
    <div align="center">    
    <div class="w3-panel w3-pale-blue">
    <h3> Bilder tagna vid varje signal innan 1a start </h3>
    </div> 
    <div align="center">
    <?php
        // Check and display the first image
        $filename = '1a_start_5_min.jpg';
        $imagePath = 'images/' . $filename; // Relative path
        if (file_exists($imagePath)) {
            $imagePath .= '?' . filemtime($imagePath);
            echo "<br> ------------------------------------------------- <p></p> ";
            echo "<h3> Bild vid varningssignal 5 minuter innan 1a start</h3>";
            echo "<img id='$filename' src='$imagePath' alt='1a_start 5 min picture' width='720' height='480'>";     
        }
        // Check and display the second image
        $filename = '1a_start_4_min.jpg';
        $imagePath = 'images/' . $filename; // Relative path
        if (file_exists($imagePath)) {
            $imagePath .= '?' . filemtime($imagePath);
            echo "<h3> Signal 4 minuter innan 1a start </h3>";
            echo "<img id='$filename' src='$imagePath' alt='1a_start 4 min picture' width='720' height='480'>";
        }
        // Check and display the third image
        $filename = '1a_start_1_min.jpg';
        $imagePath = 'images/' . $filename; // Relative path
        if (file_exists($imagePath)) {
            $imagePath .= '?' . filemtime($imagePath);
            echo "<h3> Signal 1 minuter innan 1a start </h3>";
            echo "<img id='$filename' src='$imagePath' alt='1a_start 1 min picture' width='720' height='480'>";
        }
        // Check and display the start image
        $filename = '1a_start_Start.jpg';
        $imagePath = 'images/' . $filename; // Relative path
        if (file_exists($imagePath)) {
            $imagePath .= '?' . filemtime($imagePath);
            echo "<h3> Foto vid 1a start </h3>";
            echo "<img id='$filename' src='$imagePath' alt='1a start picture' width='720' height='480'>";
        }
    ?>
    <?php
        // Check and display the first image
        $filename = '2a_start_5_min.jpg';
        $imagePath = 'images/' . $filename; // Relative path
        if (file_exists($imagePath)) {
            $imagePath .= '?' . filemtime($imagePath);
            echo "<h3> Bilder tagna vid varje signal innan 2a start  </h3> ";
            echo "<br> ------------------------------------------------- <p></p> ";
            echo "<h3> Bild vid varningssignal 5 minuter innan 2a start</h3>";
            echo "<img id='$filename' src='$imagePath' alt='2a_start 5 min picture' width='720' height=480'>";
        }
        // Check and display the second image
        $filename = '2a_start_4_min.jpg';
        $imagePath = 'images/' . $filename; // Relative path
        if (file_exists($imagePath)) {
            $imagePath .= '?' . filemtime($imagePath);
            echo "<h3> Signal 4 minuter innan 2a start </h3>";
            echo "<img id='$filename' src='$imagePath' alt='2a_start 4 min picture' width='720' height='480'>";
        }
        // Check and display the third image
        $filename = '2a_start_1_min.jpg';
        $imagePath = 'images/' . $filename; // Relative path
        if (file_exists($imagePath)) {
            $imagePath .= '?' . filemtime($imagePath);
            echo "<h3> Signal 1 minuter innan 2a start </h3>";
            echo "<img id='$filename' src='$imagePath' alt='2a_start 1 min picture' width='720' height='480'>";
        }
        // Check and display the start image
        $filename = '2a_start_Start.jpg';
        $imagePath = 'images/' . $filename; // Relative path
        if (file_exists($imagePath)) {
            $imagePath .= '?' . filemtime($imagePath);
            echo "<h3> Foto vid 2a start </h3>";
            echo "<img id='$filename' src='$imagePath' alt='2a start picture' width='720' height='480'>";
        }
    ?>
    <div class="w3-panel w3-pale-blue">
        <?php
            $video_name = 'images/video0.mp4';
            if (file_exists($video_name)) {
                echo "<h3> Video 5 min före start och 2 min efter, eller vid 2 starter, till 2 min efter andra start </h3>";
                echo '<video width = "720" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
            }
        ?>
    </div>

    <div class="w3-panel w3-pale-red">
        <?php
            for ($x = 1; $x <= $num_video; $x++) {
                $video_name = 'images/video' . $x . '.mp4';
                if (file_exists($video_name)) {
                    echo "<h2> Finish video, this is video $x for the finish</h2><br>";
                    echo '<video width = "720" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
                }
            }
        ?>  
    </div>
    <div class="w3-panel w3-grey">
        <?php
        // output index.php was last modified.
        $filename = 'index.php';
        if (file_exists($filename)) {
            echo "This web-page was last modified: \n" . date ("Y-m-d H:i:s.", filemtime($filename));
        }
        ?>
    </div>
    <div class="w3-panel w3-grey">
        <?php 
        echo " Time now: " .date("H:i:s")
        ?> 
    </div>
    </main>
</body>
</html>