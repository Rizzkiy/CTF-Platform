<?php
$flag = getenv('FLAG') ?: 'CTF{sample_flag_default}';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sample Web Challenge - CTFd-Compose</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: #1e293b;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            max-width: 500px;
            text-align: center;
            border: 1px solid #334155;
        }
        h1 {
            color: #38bdf8;
            margin-top: 0;
            font-size: 1.75rem;
        }
        p {
            color: #94a3b8;
            line-height: 1.6;
        }
        .flag-box {
            background: #0f172a;
            border: 1px dashed #38bdf8;
            color: #4ade80;
            padding: 1rem;
            font-family: monospace;
            font-size: 1.1rem;
            border-radius: 6px;
            margin: 1.5rem 0;
            word-break: break-all;
        }
        .badge {
            display: inline-block;
            background: #0369a1;
            color: #e0f2fe;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Dynamic Instance Active</span>
        <h1>CTFd-Compose Web Challenge</h1>
        <p>Congratulations! Your personal dynamic container was deployed via Docker Compose.</p>
        <div class="flag-box">
            <?php echo htmlspecialchars($flag); ?>
        </div>
        <p><small>Submit the flag above in CTFd to get your points!</small></p>
    </div>
</body>
</html>
