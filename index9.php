<?php
    define('APP_VERSION', '23.12.24'); // You can replace '1.0.0' with your desired version number
    session_id("regattastart");
    session_start();
    //echo "Session id = " . Session_id() . " ";
    // ini_set('session.gc_maxlifetime', 86400); is set in /etc/php/7.3/apache2/php.ini
    echo "Session";
    print_r($_SESSION);
    echo "<br/>";
    echo "post";
    print_r($_POST);
    echo "post <br/>";
    ini_set('display_errors', 1);
    error_reporting(E_ALL);
?>
<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Process and store the form data
    $_SESSION["form_data"] = $_POST;

    // Execute the Python script
    $command = 'python3 /usr/lib/cgi-bin/regattastart9.py ' . escapeshellarg(json_encode($_POST)) . ' > /var/www/html/output.txt 2>&1 &';
    shell_exec($command);

    echo date('h:i:s') . "<br>";
    echo "execution started";
    sleep(3);

    //exec('python3 /usr/lib/cgi-bin/regattastart9.py ' . escapeshellarg(json_encode($_POST)));
    // Redirect to index.php
    header("Location: index.php");
    exit;
}

$day = date("l");
$start_time = "18:25"; // You need to initialize $start_time
$video_end = isset($_SESSION["form_data"]["video_end"]) ? $_SESSION["form_data"]["video_end"] : "";
$num_video = isset($_SESSION["form_data"]["num_video"]) ? $_SESSION["form_data"]["num_video"] : "";
$num_starts = isset($_SESSION["form_data"]["num_starts"]) ? $_SESSION["form_data"]["num_starts"] : "";

?>
<!DOCTYPE html>
<html>
<div align="center">
<head><title> Regattastart 2024 image detection </title>   
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/w3.css"
<style>

</style>
</head>
<div class="w3-container w3-blue">
    <h2>Regattastart image detetion </h2>
</div>
<p></p>
<header>
<?php 
    echo "     Version: " . APP_VERSION . "<p></p>"; 
?>
<!-- HTML form -->
<body>
<div align="center">
<form action="index9.php" method="POST">
    <!-- Your form fields -->
    <div class="w3-container w3-pale-yellow w3-cell">
        <fieldset>
            <legend>Day and time setup: </legend>
            <?php $day = date("l") ?>
            <br>
            Day for race <select name = "day" id="day">
                <option <?php if(isset($day) && $day == "Monday"){echo "selected=\"selected\"";} ?> value="Monday">Monday</option>
                <option <?php if(isset($day) && $day == "Tuesday"){echo "selected=\"selected\"";} ?> value="Tuesday">Tuesday</option>
                <option <?php if(isset($day) && $day == "Wednesday"){echo "selected=\"selected\"";} ?> value="Wednesday">Wednesday</option>
                <option <?php if(isset($day) && $day == "Thursday"){echo "selected=\"selected\"";} ?> value="Thursday">Thursday</option>
                <option <?php if(isset($day) && $day == "Friday"){echo "selected=\"selected\"";} ?> value="Friday">Friday</option>
                <option <?php if(isset($day) && $day == "Saturday"){echo "selected=\"selected\"";} ?> value="Saturday">Saturday</option>
                <option <?php if(isset($day) && $day == "Sunday"){echo "selected=\"selected\"";} ?> value="Sunday">Sunday</option>
            </select>
            <p></p>
            <div data-tap-disabled="true">
            <?php
                $start_time = isset($_SESSION["form_data"]["start_time"]) ? $_SESSION["form_data"]["start_time"] : "";
                $steps = 5; // Set to 10, for test set to 5, You can adjust the value of $steps according to your needs
                $loops = 24 * (60 / $steps); // Define $loops here or wherever it makes sense in your code
                $current = 0; // Initialize $current
            ?>
            Start Time: <select name="start_time" id="start_time">
                <?php
                for ($i = 0; $i < $loops; $i++) {
                    $start_time_option = sprintf('%02d:%02d', $i / (60 / $steps), $current % 60);
                    $selected = ($start_time == $start_time_option) ? "selected" : ""; // Check if this option should be selected
                    echo '<option value="' . $start_time_option . '" ' . $selected . '>' . $start_time_option . '</option>';
                    $current += $steps;
                }
                ?>
            </select>
            <br>
            <p style="font-size:11px">
            (First start in case of 2 starts)
            <br>
        </fieldset>
    </div>
    <div class="w3-container w3-pale-yellow w3-cell">
        <fieldset>
            <legend>Video Setup: </legend>
            <p></p>
            End for finish video, duration from last start: 
            <select name = "video_end" id = "video_end">
                <option value="10"  <?php if(isset($video_end) && $video_end == "5"){echo "selected=\"selected\"";} ?> value="10">10</option> 
                <option value="20"  <?php if(isset($video_end) && $video_end == "20"){echo "selected=\"selected\"";} ?> value="20">20</option> 
                <option value="60" <?php if(isset($video_end) && $video_end == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
                <option value="90" <?php if(isset($video_end) && $video_end == "90"){echo "selected=\"selected\"";}?> value="90">90</option>
                <option value="120" <?php if(isset($video_end) && $video_end == "120"){echo "selected=\"selected\"";} ?> value="120">120</option>
            </select>
            <p></p>
        </fieldset>
        <p></p>
    </div>
    <br>
    <div class="w3-row-padding" align="center">
        <div class="w3-container w3-light-grey w3-cell">
            <fieldset>
                <legend> Setup of 1 or 2 starts </legend>
                <p></p>
                Number of starts: <select name="num_starts" id="num_starts">
                    <option <?php if(isset($num_starts) && $num_starts == "1"){echo "selected=\"selected\"";} ?> value="1">1</option>
                    <option <?php if(isset($num_starts) && $num_starts == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
                </select>
            </fieldset>
            <p></p>
        </div>
    </div>
    <br>
    <div class="w3-row-padding" align="center">
        <div class="w3-container w3-blue w3-cell">
            <fieldset>
                <legend>Execute</legend>
                <div id="submit" align="center"></div>
                    <div class="w3" align="center">
                        <p>
                    <button type="submit">Submit</button>
                </div>
                <p></p>
            </fieldset>
            <p></p>
        </div>
    </div>
</form>
</div>     
<!-- Here is our page's main content -->
<main>
    <br>
    <div id="result" align="center"></div>
    <div class="w3" align="center">
    <br>
    <h5> <a href="/index.php">  Resultat sida  </a></h5>
    </div>
</main>
<footer>
    <div class="w3-row-padding" align="center">
        <br><p> - phwe - <br></p>
    </div>
</footer>
</body>
</html>
<?php
    // output when index9.php was last modified.
    $filename = 'index9.php';
    if (file_exists($filename)) {
        echo "        This web-page: $filename was last modified: " . date ("Y-m-d H:i:s.", filemtime($filename));
    }
?>
