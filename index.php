<?php
    define('APP_VERSION', '23.11.0'); // You can replace '1.0.0' with your desired version number
    session_id("regattastart");
    session_start();
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    ini_set('display_errors', 1); 
    error_reporting(E_ALL);
?>
<!-- Your HTML to display data from the session -->
<!DOCTYPE html>
<html>
<head>
    <title>Regattastart</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
    <link rel="stylesheet" href="/w3.css"
    </head>
<body>
<div align="center">
    <div class="w3-panel w3-blue">
        <h2> Regattastart  </h2>
    </div>
<?php 
    echo "     Version: " . APP_VERSION . "<br><p></p>"; 
?>
<?php
// Retrieve and display data from the session
if (isset($_SESSION["form_data"])) {
    $form_data = $_SESSION["form_data"];
    // Display the data or do whatever you need
    echo "Start time: " . $form_data['start_time'];
    echo ", Video Delay: " . $form_data['video_delay'];
    echo ", Video Duration: " . $form_data['video_dur'];
    $num_video = $form_data['num_video'];
    echo ", Number of Videos: " . $num_video;
    $num_starts = $form_data['num_starts'];
    echo ", Number of starts: " . $num_starts;
}
?>
</div>
<!-- Here is our page's main content -->
<main>
<div align="center">
<h4><a href="/index6.php" title="Merged 1 and 2 start versions together"> Setup Page </a></h4>
<div align="center">
<div class="w3-panel w3-pale-blue">
<h3> Bilder tagna vid varje signal innan 1a start </h3>
</div> 
<h3> Bild vid varningssignal 5 minuter innan 1a start</h3>
<img src="/images/1:a_start_5_min.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="1st 5 min picture" width="720" height="480"  >
<h3> Bild vid signal 4 minuter innan 1a start</h3>
<img src="/images/1:a_start_4_min.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="1st 4 min picture" width="720" height="480"  >
<h3> Bild vid signal 1 minut innan 1a start</h3>
<img src="/images/1:a_start_1_min.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="1st 1 min picture" width="720" height="480"  >
<h3> Foto vid 1a start</h3>
<img src="/images/1:a_start_Start.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="1st start  picture" width="720" height="480"  >
<?php
    $path = '/images/';
    $filename = 'images/2:a_start_5_min.jpg';
    if (file_exists($filename)) {
       echo "<h3> Bilder tagna vid varje signal innan 2a start  </h3> ";
       echo "<br> ------------------------------------------------- <p></p> ";
       $filename = '2:a_start_5_min.'.jpg';
       echo "<h3> Bild vid varningssignal 5 minuter innan 2a start</h3>";
       echo '<img src = "' . $path . $filename . '" / alt="1st 5 min picture" width="720" height="480"  >';
       $filename = '2:a_start_4_min.jpg';
       echo "<h3> Signal 4 minuter innan 2a start </h3>";
       echo '<img src = "' . $path . $filename . '" / alt="1st 5 min picture" width="720" height="480"  >';
       $filename = '2:a_start_1_min..jpg';
       echo "<h3> Signal 1 minut innan 2a start </h3>";
       echo '<img src = "' . $path . $filename . '" / alt="1st 5 min picture" width="720" height="480"  >';
       $filename = '2:a_start_Start.jpg';
       echo "<h3> Foto vid 2a start </h3>";
       echo '<img src = "' . $path . $filename . '" / alt="1st 5 min picture" width="720" height="480"  >';
    }
?>
<div class="w3-panel w3-pale-blue">
    <?php
        $video_name = '/images/video0.mp4';
        {
           echo "<h3> Video 5 min före start och 2 min efter, eller vid 2 starter, till 2 min efter andra start </h3>";
           echo '<video width = "720" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
        }
    ?>
</div>
<div class="w3-panel w3-pale-red">
    <?php
        for ($x = 1; $x <= $num_video; $x++) {
            echo "<h2> Finish video, this is video $x for the finish</h2><br>";
            $video_name =  "/images/video" . $x . ".mp4";
            echo '<video width = "720" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
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
