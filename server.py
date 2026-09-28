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
        body {
            background-color: #f5f2e9;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }

        .container {
            width: 100%;
            max-width: 420px;
            background: #fdfbf7;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            text-align: center;
        }

        .header-logo {
            max-width: 100%;
            height: auto;
            margin-bottom: 10px;
        }

        .subtitle-container {
            margin: 15px 0 20px 0;
        }

        .subtitle-banner {
            max-width: 90%;
            height: auto;
        }

        .form-group {
            margin-bottom: 18px;
            text-align: center;
        }

        .label-img {
            height: 22px;
            width: auto;
            display: block;
            margin: 0 auto 6px auto;
        }

        .custom-dropdown {
            width: 100%;
            padding: 12px;
            border-radius: 25px;
            border: 1px solid #c8d1d3;
            background: linear-gradient(180deg, #ffffff 0%, #edf2f4 100%);
            font-size: 16px;
            font-weight: bold;
            color: #2b3a42;
            text-align: center;
            outline: none;
            cursor: pointer;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
        }

        .lang-selector {
            margin-bottom: 15px;
        }

        .lang-btn {
            background: #5b7f36;
            color: white;
            border: none;
            padding: 6px 12px;
            margin: 0 4px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 12px;
        }
    </style>
</head>
<body>

<div class="container">
    <!-- Language Switcher -->
    <div class="lang-selector">
        <button class="lang-btn" onclick="setLanguage('en')">English</button>
        <button class="lang-btn" onclick="setLanguage('ur')">اردو</button>
        <button class="lang-btn" onclick="setLanguage('ar')">العربية</button>
    </div>

    <!-- Header Section -->
    <div class="header-section">
        <img src="LRM-E.png?v=1.2" id="header-logo" class="header-logo" alt="The Qari">
    </div>

    <!-- Subtitle Banner: MEMORIZE WITH PERFECTION -->
    <div class="subtitle-container">
        <img id="mwp-banner" class="subtitle-banner" src="mwp.png?v=1.2" alt="Memorize With Perfection">
    </div>

    <!-- Surah Selection -->
    <div class="form-group">
        <img id="lbl-surah" class="label-img" src="ne.png?v=1.2" alt="Surah No. / Name">
        <select id="surah-select" class="custom-dropdown">
            <option value="102">Surah At-Takathur &nbsp;&nbsp;&nbsp; 102 &nbsp;&nbsp;&nbsp; سُورَةُ التَّكَاثُر</option>
        </select>
    </div>

    <!-- Juz Selection -->
    <div class="form-group">
        <img id="lbl-juz" class="label-img" src="juzn.png?v=1.2" alt="Juz No. / Name">
        <select id="juz-select" class="custom-dropdown">
            <option value="">- Select The Juz -</option>
        </select>
    </div>

    <!-- Ayah Selection -->
    <div class="form-group">
        <img id="lbl-ayah" class="label-img" src="ae.png?v=1.2" alt="Aayah / Verse No.">
        <select id="ayah-select" class="custom-dropdown">
            <option value="">- Select The Ayah -</option>
        </select>
    </div>
</div>

<script>
    function setLanguage(lang) {
        const mwpBanner = document.getElementById('mwp-banner');
        const lblSurah = document.getElementById('lbl-surah');
        const lblJuz = document.getElementById('lbl-juz');
        const lblAyah = document.getElementById('lbl-ayah');

        if (lang === 'ur') {
            mwpBanner.src = 'mwpu.png?v=1.2';
            lblSurah.src = 'nu.png?v=1.2';
            lblJuz.src = 'juznu.png?v=1.2';
            lblAyah.src = 'au.png?v=1.2';
        } else if (lang === 'ar') {
            mwpBanner.src = 'mwpua.png?v=1.2';
            lblSurah.src = 'nea.png?v=1.2';
            lblJuz.src = 'juzna.png?v=1.2';
            lblAyah.src = 'aea.png?v=1.2';
        } else {
            // Default: English
            mwpBanner.src = 'mwp.png?v=1.2';
            lblSurah.src = 'ne.png?v=1.2';
            lblJuz.src = 'juzn.png?v=1.2';
            lblAyah.src = 'ae.png?v=1.2';
        }
    }
</script>

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
    app.run(host="0.0.0.0", port=5000, debug=True)