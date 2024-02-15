<?php
    define('APP_VERSION', '24.02.09'); // You can replace '1.0.0' with your desired version number
    session_id("regattastart");
    session_start();
    //echo "Session id = " . Session_id() . " ";
    // ini_set('session.gc_maxlifetime', 86400); is set in /etc/php/7.3/apache2/php.ini
    //print_r($_SESSION);
    //echo "<br/>";
    //print_r($_POST);
    //echo "<br/>";
    ini_set('display_errors', 1);
    error_reporting(E_ALL);
?>
<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Process and store the form data
    $_SESSION["form_data"] = $_POST;

    // Execute the Python script
    $command = 'python3 /usr/lib/cgi-bin/regattastart6.py ' . escapeshellarg(json_encode($_POST)) . ' > /var/www/html/output.txt 2>&1 &';
    shell_exec($command);
    
    echo date('h:i:s') . "<br>";
    echo "execution started";
    sleep(3);
    
    //exec('python3 /usr/lib/cgi-bin/regattastart6.py ' . escapeshellarg(json_encode($_POST)));
    // Redirect to index.php
    header("Location: index.php");
    exit;
}

$day = date("l");
$start_time = "18:25"; // You need to initialize $start_time
$video_delay = isset($_SESSION["form_data"]["video_delay"]) ? $_SESSION["form_data"]["video_delay"] : "";
$video_dur = isset($_SESSION["form_data"]["video_dur"]) ? $_SESSION["form_data"]["video_dur"] : "";
$num_video = isset($_SESSION["form_data"]["num_video"]) ? $_SESSION["form_data"]["num_video"] : "";
$num_starts = isset($_SESSION["form_data"]["num_starts"]) ? $_SESSION["form_data"]["num_starts"] : "";
?>
<!DOCTYPE html>
<html>
<head>
    <title> Regattastart 2024 för setup av en eller 2 starter </title> 
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- set styles -->
    <style>
        img {
            max-width: 100%;
            height: auto;
        }
        video {
            max-width: 100%;
            height: auto;
        }
        .container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh; /* Optional: Makes the container full height */
        }
        .form-container {
            display: flex;
            justify-content: center;
            align-items: center;
            /* height: 100vh; /* Adjust as needed */
            width: 80%; /* Adjust width as needed */
            margin: 0 auto; /* Center horizontally */
        }
        .form-container fieldset {
            margin-bottom: 20px;
        }
        .form-container select {
            width: 100%;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ccc;
            margin-bottom: 10px;
        }
        .form-container button[type="submit"] {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            background-color: #007bff;
            color: #fff;
            cursor: pointer;
        }
    </style>
    <link rel="stylesheet" href="/w3.css">
</head>
<div style="text-align: center;" class="w3-container w3-blue">
    <h2>Regattastart for 1 or 2 starts </h2>
</div>
<header>
<div style="text-align: center;">
    <?php 
        echo "     Version: " . APP_VERSION . "<p></p>"; 
    ?>
</div>
<!-- HTML form -->
<body>
    <div class="form-container">
        <div style="text-align: center;">
            <form action="index6.php" method="POST">
                <!-- Your form fields -->
                <div class="w3-row-padding">
                    <div class="w3-cell w3-pale-yellow">
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
                    <div class="w3-form-container w3-cell w3-pale-yellow">
                        <fieldset>
                        <legend>Video Setup: </legend>
                        <p></p>
                        Duration between start and estimated finish: 
                        <select name = "video_delay" id = "video_delay">
                            <option value="5" <?php if(isset($video_delay) && $video_delay == "5"){echo "selected=\"selected\"";}  ?>>5</option>
                            <option value="20" <?php if(isset($video_delay) && $video_delay == "20"){echo "selected=\"selected\"";} ?>>20</option>
                            <option value="30" <?php if(isset($video_delay) && $video_delay == "30"){echo "selected=\"selected\"";} ?>>30</option>
                            <option value="40" <?php if(isset($video_delay) && $video_delay == "40"){echo "selected=\"selected\"";} ?>>40</option>
                            <option value="50" <?php if(isset($video_delay) && $video_delay == "50"){echo "selected=\"selected\"";} ?>>50</option>
                            <option value="60" <?php if(isset($video_delay) && $video_delay == "60"){echo "selected=\"selected\"";} ?>>60</option>
                            <option value="70" <?php if(isset($video_delay) && $video_delay == "70"){echo "selected=\"selected\"";} ?>>70</option>
                            <option value="80" <?php if(isset($video_delay) && $video_delay == "80"){echo "selected=\"selected\"";} ?>>80</option>
                        </select>
                        <p></p>
                        Duration for each video: 
                        <select name = "video_dur" id = "video_dur">
                            <option value="2"  <?php if(isset($video_dur) && $video_dur == "2"){echo "selected=\"selected\"";} ?> value="2">2</option> 
                            <option value="10" <?php if(isset($video_dur) && $video_dur == "10"){echo "selected=\"selected\"";} ?> value="10">10</option>
                            <option value="15" <?php if(isset($video_dur) && $video_dur == "15"){echo "selected=\"selected\"";}?> value="15">15</option>
                            <option value="20" <?php if(isset($video_dur) && $video_dur == "20"){echo "selected=\"selected\"";} ?> value="20">20</option>
                            <option value="30" <?php if(isset($video_dur) && $video_dur == "30"){echo "selected=\"selected\"";} ?> value="30">30</option>
                            <option value="50" <?php if(isset($video_dur) && $video_dur == "50"){echo "selected=\"selected\"";} ?> value="50">50</option>
                            <option value="60" <?php if(isset($video_dur) && $video_dur == "60"){echo "selected=\"selected\"";} ?> value="60">60</option> 
                        </select>
                        <p></p>
                        Number of video's: 
                        <select name = "num_video" id = "num_video">
                            <option <?php if(isset($num_video) && $num_video == "9"){echo "selected=\"selected\"";} ?> value="9">9</option>
                            <option <?php if(isset($num_video) && $num_video == "8"){echo "selected=\"selected\"";} ?> value="8">8</option>
                            <option <?php if(isset($num_video) && $num_video == "7"){echo "selected=\"selected\"";} ?> value="7">7</option>
                            <option <?php if(isset($num_video) && $num_video == "6"){echo "selected=\"selected\"";} ?> value="6">6</option>
                            <option <?php if(isset($num_video) && $num_video == "5"){echo "selected=\"selected\"";} ?> value="5">5</option>
                            <option <?php if(isset($num_video) && $num_video == "4"){echo "selected=\"selected\"";} ?> value="4">4</option>
                            <option <?php if(isset($num_video) && $num_video == "3"){echo "selected=\"selected\"";} ?> value="3">3</option>
                            <option <?php if(isset($num_video) && $num_video == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
                            <option <?php if(isset($num_video) && $num_video == "1"){echo "selected=\"selected\"";} ?> value="1">1</option>
                        </select>
                        </fieldset>
                    </div>
                </div>
                <div class="w3-row-padding">
                    <div class="w3-form-container w3-light-grey w3-cell">
                        <fieldset>
                            <legend> Setup of 1 or 2 starts </legend>
                            <p></p>
                            Number of starts: <select name="num_starts" id="num_starts">
                                <option <?php if(isset($num_starts) && $num_starts == "1"){echo "selected=\"selected\"";} ?> value="1">1</option>
                                <option <?php if(isset($num_starts) && $num_starts == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
                            </select>
                        </fieldset>
                    </div>
                </div>
                <br>
                <div class="w3-row-padding">
                    <div class="w3-form-container w3-blue w3-cell">
                        <fieldset>
                            <legend>Execute</legend>
                            <div style="text-align: center" id="submit"></div>
                                <button type="submit">Submit</button>
                        </fieldset>
                    </div>
                </div>
            </form>
        </div>
    </div>
<!-- Here is our page's main content -->
<main>
    <br>
    <div id="result" ></div>
    <<div style="text-align: center;">
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
    // output when index6.php was last modified.
    $filename = 'index6.php';
    if (file_exists($filename)) {
        echo "        This web-page: $filename was last modified: " . date ("Y-m-d H:i:s.", filemtime($filename));
    }
?>
