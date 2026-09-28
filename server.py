import os
from flask import Flask, render_template_string, send_from_directory

app = Flask(__name__, static_folder=".")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Qari - Khudem Al-Quran</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background: url('background_clean.jpg') no-repeat center top;
            background-size: cover;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            padding: 10px;
        }

        .container {
            width: 100%;
            max-width: 380px;
            background: transparent;
            padding: 10px;
            text-align: center;
            position: relative;
        }

        /* Header Logo */
        .header-logo {
            width: 100%;
            height: auto;
            display: block;
            margin: 0 auto 5px auto;
        }

        /* Generic CSS Multilingual Animation Container */
        .fade-slot {
            position: relative;
            display: inline-block;
            vertical-align: middle;
            overflow: hidden;
        }

        .fade-slot img {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            opacity: 0;
            animation: langFade 27s infinite;
        }

        /* 27s Total Cycle: 9s per language (English -> Arabic -> Urdu) */
        .fade-slot img:nth-child(1) { animation-delay: 0s; }   /* English */
        .fade-slot img:nth-child(2) { animation-delay: 9s; }   /* Arabic  */
        .fade-slot img:nth-child(3) { animation-delay: 18s; }  /* Urdu    */

        @keyframes langFade {
            0% { opacity: 0; }
            1.85% { opacity: 1; }   /* Crossfade in over 0.5s */
            31.48% { opacity: 1; }  /* Hold visible until 8.5s */
            33.33% { opacity: 0; }  /* Crossfade out completely at 9.0s */
            100% { opacity: 0; }
        }

        /* Slot Dimensions matching baseline placement */
        .slot-mwp { width: 100%; height: 32px; margin: 8px 0 10px 0; }
        .slot-label { width: 100%; height: 18px; margin-bottom: 4px; }
        .slot-repeat { width: 100%; height: 20px; margin: 12px 0 8px 0; }
        .slot-times { width: 65px; height: 14px; margin-top: 2px; }
        .slot-btn { width: 65px; height: 18px; }

        /* Form Group Styling */
        .form-group {
            margin-bottom: 12px;
            text-align: center;
        }

        .custom-dropdown {
            width: 100%;
            padding: 10px 12px;
            border-radius: 25px;
            border: 1px solid #b2c2a8;
            background: linear-gradient(180deg, #ffffff 0%, #edf2f4 100%);
            font-size: 14px;
            font-weight: bold;
            color: #2b3a42;
            text-align: center;
            outline: none;
            cursor: pointer;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);
        }

        /* Repeats & Controls Grid */
        .repeat-grid, .controls-grid {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .repeat-card {
            flex: 1;
            margin: 0 3px;
            background: linear-gradient(180deg, #e4ede0 0%, #c1d5b9 100%);
            border: 1px solid #9cb592;
            border-radius: 10px;
            padding: 8px 4px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        }

        .repeat-num {
            font-size: 24px;
            font-weight: 900;
            color: #3b5228;
            line-height: 1;
        }

        .ctrl-btn {
            flex: 1;
            margin: 0 3px;
            background: linear-gradient(180deg, #ffffff 0%, #e1e6e8 100%);
            border: 1px solid #b0bec5;
            border-radius: 20px;
            padding: 8px 0;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>

<div class="container">

    <!-- Header Logo -->
    <img src="LRM-E.png?v=4.0" class="header-logo" alt="The Qari">

    <!-- Subtitle Banner: MEMORIZE WITH PERFECTION (Eng / Ar / Ur) -->
    <div class="fade-slot slot-mwp">
        <img src="mwp.png?v=4.0" alt="Memorize With Perfection (EN)">
        <img src="mwpua.png?v=4.0" alt="Memorize With Perfection (AR)">
        <img src="mwpu.png?v=4.0" alt="Memorize With Perfection (UR)">
    </div>

    <!-- Surah Selection Label & Dropdown -->
    <div class="form-group">
        <div>
            <div class="fade-slot slot-label">
                <img src="sn.png?v=4.0" alt="Surah Label (EN)">
                <img src="sna.png?v=4.0" alt="Surah Label (AR)">
                <img src="snu.png?v=4.0" alt="Surah Label (UR)">
            </div>
        </div>
        <select id="surah-select" class="custom-dropdown">
            <option value="102">Surah At-Takathur &nbsp;&nbsp; 102 &nbsp;&nbsp; سُورَةُ التَّكَاثُر</option>
        </select>
    </div>

    <!-- Juz Selection Label & Dropdown -->
    <div class="form-group">
        <div>
            <div class="fade-slot slot-label">
                <img src="juzn.png?v=4.0" alt="Juz Label (EN)">
                <img src="juzna.png?v=4.0" alt="Juz Label (AR)">
                <img src="juznu.png?v=4.0" alt="Juz Label (UR)">
            </div>
        </div>
        <select id="juz-select" class="custom-dropdown">
            <option value="">- Select The Juz -</option>
        </select>
    </div>

    <!-- Ayah Selection Label & Dropdown -->
    <div class="form-group">
        <div>
            <div class="fade-slot slot-label">
                <img src="avn.png?v=4.0" alt="Ayah Label (EN)">
                <img src="avna.png?v=4.0" alt="Ayah Label (AR)">
                <img src="avnu.png?v=4.0" alt="Ayah Label (UR)">
            </div>
        </div>
        <select id="ayah-select" class="custom-dropdown">
            <option value="">- Select The Ayah -</option>
        </select>
    </div>

    <!-- Please Set Recitation Repeats Header -->
    <div>
        <div class="fade-slot slot-repeat">
            <img src="PLSE.png?v=4.0" alt="Please Set Repeats (EN)">
            <img src="PLSA.png?v=4.0" alt="Please Set Repeats (AR)">
            <img src="PLSU.png?v=4.0" alt="Please Set Repeats (UR)">
        </div>
    </div>

    <!-- Repeats Cards (21, 10, 5) with TIMES PNGs -->
    <div class="repeat-grid">
        <div class="repeat-card">
            <span class="repeat-num">21</span>
            <div class="fade-slot slot-times">
                <img src="rte.png?v=4.0" alt="TIMES (EN)">
                <img src="rta.png?v=4.0" alt="TIMES (AR)">
                <img src="rtu.png?v=4.0" alt="TIMES (UR)">
            </div>
        </div>
        <div class="repeat-card">
            <span class="repeat-num">10</span>
            <div class="fade-slot slot-times">
                <img src="rte.png?v=4.0" alt="TIMES (EN)">
                <img src="rta.png?v=4.0" alt="TIMES (AR)">
                <img src="rtu.png?v=4.0" alt="TIMES (UR)">
            </div>
        </div>
        <div class="repeat-card">
            <span class="repeat-num">5</span>
            <div class="fade-slot slot-times">
                <img src="rte.png?v=4.0" alt="TIMES (EN)">
                <img src="rta.png?v=4.0" alt="TIMES (AR)">
                <img src="rtu.png?v=4.0" alt="TIMES (UR)">
            </div>
        </div>
    </div>

    <!-- Navigation Control Buttons -->
    <div class="controls-grid">
        <button class="ctrl-btn">
            <div class="fade-slot slot-btn">
                <img src="pve.png?v=4.0" alt="PREV (EN)">
                <img src="pva.png?v=4.0" alt="PREV (AR)">
                <img src="pvu.png?v=4.0" alt="PREV (UR)">
            </div>
        </button>
        <button class="ctrl-btn">
            <div class="fade-slot slot-btn">
                <img src="ae.png?v=4.0" alt="AGAIN (EN)">
                <img src="aea.png?v=4.0" alt="AGAIN (AR)">
                <img src="au.png?v=4.0" alt="AGAIN (UR)">
            </div>
        </button>
        <button class="ctrl-btn">
            <div class="fade-slot slot-btn">
                <img src="ne.png?v=4.0" alt="NEXT (EN)">
                <img src="nea.png?v=4.0" alt="NEXT (AR)">
                <img src="nu.png?v=4.0" alt="NEXT (UR)">
            </div>
        </button>
    </div>

</div>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/<path:filename>")
def serve_assets(filename):
    return send_from_directory(".", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8787, debug=True)