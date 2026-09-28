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
            background: url('background_clean.jpg') no-repeat center center fixed;
            background-size: cover;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            width: 100%;
            max-width: 420px;
            background: rgba(253, 251, 247, 0.92);
            border-radius: 20px;
            padding: 25px 20px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
            text-align: center;
            position: relative;
        }

        /* Top Header Image */
        .header-logo {
            width: 100%;
            height: auto;
            display: block;
            margin: 0 auto 10px auto;
        }

        /* Generic CSS Multilingual Cross-fade Slot */
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
            animation: langFade 15s infinite;
        }

        /* 15s Cycle (5s per language with 0.5s smooth cross-fade) */
        .fade-slot img:nth-child(1) { animation-delay: 0s; }
        .fade-slot img:nth-child(2) { animation-delay: 5s; }
        .fade-slot img:nth-child(3) { animation-delay: 10s; }

        @keyframes langFade {
            0% { opacity: 0; }
            3.33% { opacity: 1; }   /* Fade in complete at 0.5s */
            30% { opacity: 1; }     /* Hold until 4.5s */
            33.33% { opacity: 0; }  /* Fade out complete at 5.0s */
            100% { opacity: 0; }
        }

        /* Precise Slot Dimensions (Preserves 100% Layout Alignment) */
        .slot-mwp { width: 100%; height: 32px; margin: 10px 0 15px 0; }
        .slot-label { width: 220px; height: 22px; margin-bottom: 6px; }
        .slot-repeat { width: 300px; height: 22px; margin: 18px 0 10px 0; }
        .slot-times { width: 70px; height: 16px; margin-top: 4px; }
        .slot-btn { width: 65px; height: 20px; }

        /* Dropdown Styling */
        .form-group {
            margin-bottom: 16px;
            text-align: center;
        }

        .custom-dropdown {
            width: 100%;
            padding: 12px 15px;
            border-radius: 25px;
            border: 1px solid #b2c2a8;
            background: linear-gradient(180deg, #ffffff 0%, #edf2f4 100%);
            font-size: 15px;
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
            margin-bottom: 15px;
        }

        .repeat-card {
            flex: 1;
            margin: 0 4px;
            background: linear-gradient(180deg, #e4ede0 0%, #c1d5b9 100%);
            border: 1px solid #9cb592;
            border-radius: 12px;
            padding: 10px 5px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.08);
        }

        .repeat-num {
            font-size: 26px;
            font-weight: 900;
            color: #3b5228;
            line-height: 1;
        }

        .ctrl-btn {
            flex: 1;
            margin: 0 4px;
            background: linear-gradient(180deg, #ffffff 0%, #e1e6e8 100%);
            border: 1px solid #b0bec5;
            border-radius: 20px;
            padding: 10px 0;
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

    <!-- Top Logo Header -->
    <img src="LRM-E.png?v=2.0" classheader-logo" alt="The Qari">

    <!-- Subtitle Banner: MEMORIZE WITH PERFECTION (Eng / Ur / Ar) -->
    <div class="fade-slot slot-mwp">
        <img src="mwp.png?v=2.0" alt="Memorize With Perfection (EN)">
        <img src="mwpu.png?v=2.0" alt="Memorize With Perfection (UR)">
        <img src="mwpua.png?v=2.0" alt="Memorize With Perfection (AR)">
    </div>

    <!-- Surah Selection Label & Dropdown -->
    <div class="form-group">
        <div>
            <div class="fade-slot slot-label">
                <img src="ne.png?v=2.0" alt="Surah Label (EN)">
                <img src="nu.png?v=2.0" alt="Surah Label (UR)">
                <img src="nea.png?v=2.0" alt="Surah Label (AR)">
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
                <img src="juzn.png?v=2.0" alt="Juz Label (EN)">
                <img src="juznu.png?v=2.0" alt="Juz Label (UR)">
                <img src="juzna.png?v=2.0" alt="Juz Label (AR)">
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
                <img src="ae.png?v=2.0" alt="Ayah Label (EN)">
                <img src="au.png?v=2.0" alt="Ayah Label (UR)">
                <img src="aea.png?v=2.0" alt="Ayah Label (AR)">
            </div>
        </div>
        <select id="ayah-select" class="custom-dropdown">
            <option value="">- Select The Ayah -</option>
        </select>
    </div>

    <!-- Repeats Instruction Header (Eng / Ur / Ar) -->
    <div>
        <div class="fade-slot slot-repeat">
            <img src="PLSE.png?v=2.0" alt="Please Set Recitation Repeats (EN)">
            <img src="PLSU.png?v=2.0" alt="Please Set Recitation Repeats (UR)">
            <img src="PLSA.png?v=2.0" alt="Please Set Recitation Repeats (AR)">
        </div>
    </div>

    <!-- 21 / 10 / 5 Repeats Cards with Multilingual TIMES -->
    <div class="repeat-grid">
        <div class="repeat-card">
            <span class="repeat-num">21</span>
            <div class="fade-slot slot-times">
                <img src="rte.png?v=2.0" alt="TIMES (EN)">
                <img src="rtu.png?v=2.0" alt="TIMES (UR)">
                <img src="rta.png?v=2.0" alt="TIMES (AR)">
            </div>
        </div>
        <div class="repeat-card">
            <span class="repeat-num">10</span>
            <div class="fade-slot slot-times">
                <img src="rte.png?v=2.0" alt="TIMES (EN)">
                <img src="rtu.png?v=2.0" alt="TIMES (UR)">
                <img src="rta.png?v=2.0" alt="TIMES (AR)">
            </div>
        </div>
        <div class="repeat-card">
            <span class="repeat-num">5</span>
            <div class="fade-slot slot-times">
                <img src="rte.png?v=2.0" alt="TIMES (EN)">
                <img src="rtu.png?v=2.0" alt="TIMES (UR)">
                <img src="rta.png?v=2.0" alt="TIMES (AR)">
            </div>
        </div>
    </div>

    <!-- Control Buttons: PREV / AGAIN / NEXT -->
    <div class="controls-grid">
        <button class="ctrl-btn">
            <div class="fade-slot slot-btn">
                <img src="pve.png?v=2.0" alt="PREV (EN)">
                <img src="pvu.png?v=2.0" alt="PREV (UR)">
                <img src="pva.png?v=2.0" alt="PREV (AR)">
            </div>
        </button>
        <button class="ctrl-btn">
            <div class="fade-slot slot-btn">
                <img src="avn.png?v=2.0" alt="AGAIN (EN)">
                <img src="avnu.png?v=2.0" alt="AGAIN (UR)">
                <img src="avna.png?v=2.0" alt="AGAIN (AR)">
            </div>
        </button>
        <button class="ctrl-btn">
            <div class="fade-slot slot-btn">
                <img src="ne.png?v=2.0" alt="NEXT (EN)">
                <img src="nu.png?v=2.0" alt="NEXT (UR)">
                <img src="nea.png?v=2.0" alt="NEXT (AR)">
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