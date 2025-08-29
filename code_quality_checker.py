import subprocess
import smtplib
import os
import logging
import sys
import time
import shutil
import re
from threading import Thread
from flask import Flask, request, jsonify
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from git import Repo, GitCommandError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

''' Configure logging to console + file with flushing '''
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("webhook.log", mode="a")
    ]
)
logger = logging.getLogger(__name__)

''' Create Flask app '''
app = Flask(__name__)

''' Email credentials and details stored in a dictionary '''
EMAIL_CONFIG = {
    'sender': 'faizanlodhi.pro1@gmail.com',
    'password': 'gollzcfqauwzigxk',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'manager_recipient': 'kashif.manzoor@axiomworld.net',
}


# ----------------- EMAIL -----------------
# ----------------- EMAIL -----------------
def create_professional_email_body(repo_name, commit_id, issues, repo_url, branch_name, pylint_score=None):
    """Create a professional HTML email body with Pylint score"""
    commit_short = commit_id[:8] if commit_id else "N/A"
    issues_count = len(issues) if issues else 0
    files_count = len(set(issue['file'] for issue in issues)) if issues else 0

    # Build issues section if there are issues
    issues_section = ""
    if issues:
        issues_by_file = {}
        for issue in issues:
            issues_by_file.setdefault(issue['file'], []).append(issue)

        issues_section = """
            <div class="card error">
                <h3>🚨 Code Quality Issues Found</h3>
        """

        for file, file_issues in issues_by_file.items():
            issues_section += f"""
                <div class="file-header">
                    <h4>📄 {file}</h4>
                    <p>{len(file_issues)} issue(s)</p>
                </div>
            """
            for issue in file_issues:
                issues_section += f"""
                    <div class="issue">
                        <strong>{issue['tool']}:</strong> {issue['message']}<br>
                        <small>Line {issue.get('line', 'N/A')} | {issue.get('code', '')}</small>
                    </div>
                """

        issues_section += "</div>"
    else:
        issues_section = """
            <div class="card success">
                <h3>🎉 Excellent Work!</h3>
                <p>All code quality checks have passed successfully. The code meets our quality standards.</p>
            </div>
        """

    # Build pylint score section if available
    pylint_section = ""
    if pylint_score is not None:
        pylint_section = f"""
            <div class="pylint-score">
                <h3>Pylint Score</h3>
                <div class="score-circle" style="--score: {pylint_score * 10}%;">
                    <span class="score-value">{pylint_score:.2f}/10</span>
                </div>
                <div class="score-text">A higher score means better code quality.</div>
            </div>
        """

    # Single HTML template
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 20px; text-align: center; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; background: #f9f9f9; }}
            .card {{ background: white; border-radius: 10px; padding: 20px; margin: 20px 0; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .success {{ border-left: 4px solid #28a745; }}
            .warning {{ border-left: 4px solid #ffc107; }}
            .error {{ border-left: 4px solid #dc3545; }}
            .issue {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 5px; 
                     border-left: 3px solid #ffc107; }}
            .file-header {{ background: #e9ecef; padding: 10px; border-radius: 5px; margin: 10px 0; }}
            .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat-item {{ text-align: center; padding: 15px; background: white; 
                         border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .footer {{ text-align: center; margin-top: 30px; padding: 20px; background: #343a40; color: white; }}

            /* Fixed Pylint Score UI */
            .pylint-score {{
                text-align: center;
                margin: 20px 0;
            }}
            .score-circle {{
                --score: 75%;
                width: 120px;
                height: 120px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                font-weight: bold;
                color: #333;
                background: conic-gradient(
                    #4CAF50 var(--score),
                    #e0e0e0 var(--score)
                );
                margin: 0 auto;
                position: relative;
            }}
            .score-value {{
                position: absolute;
                font-size: 18px;
                font-weight: bold;
                color: #000;
            }}
            .score-text {{
                margin-top: 10px;
                font-size: 14px;
                font-weight: bold;
                color: #555;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 Code Quality Report</h1>
            <p>Axiom World - Automated Code Review System</p>
        </div>

        <div class="container">
            <div class="card {'success' if not issues else 'warning'}">
                <h2>Repository: {repo_name}</h2>
                <p><strong>Branch:</strong> {branch_name}</p>
                <p><strong>Commit:</strong> <code>{commit_short}</code></p>
                <p><strong>Status:</strong> {'✅ All checks passed' if not issues else '⚠️ Issues detected'}</p>
            </div>

            {pylint_section}

            <div class="stats">
                <div class="stat-item">
                    <h3>📊 Files Changed</h3>
                    <p>{files_count}</p>
                </div>
                <div class="stat-item">
                    <h3>⚠️ Total Issues</h3>
                    <p>{issues_count}</p>
                </div>
                <div class="stat-item">
                    <h3>🔧 Tools Used</h3>
                    <p>Pylint + Black</p>
                </div>
            </div>

            {issues_section}

            <div class="card">
                <h3>🔗 Repository Details</h3>
                <p><strong>URL:</strong> <a href="{repo_url}">{repo_url}</a></p>
                <p><strong>Commit Hash:</strong> <code>{commit_id}</code></p>
                <p><strong>Review Time:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="card">
                <h3>📋 Next Steps</h3>
                <p>{"Please review the issues above and fix them before merging." if issues else "You can proceed with merging this code."}</p>
                <p>For questions, contact the development team.</p>
            </div>
        </div>

        <div class="footer">
            <p>📧 This is an automated message from Axiom World Code Quality System</p>
            <p>📍 Generated on {time.strftime('%Y-%m-%d at %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """

    return html_template


def send_email(subject, repo_name, commit_id, issues, repo_url, branch_name, pylint_score=None, employee_email=None):
    """Send professional email notification to both manager and employee using single template"""
    try:
        # Create HTML email using single template
        html_body = create_professional_email_body(repo_name, commit_id, issues, repo_url, branch_name, pylint_score)

        msg = MIMEMultipart('alternative')  # You can keep this, as it's the correct type for HTML
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = EMAIL_CONFIG['manager_recipient']
        if employee_email:
            msg['Cc'] = employee_email
        # Create only the HTML part
        part2 = MIMEText(html_body, 'html')

        # Attach only the HTML part
        msg.attach(part2)

        recipients = [EMAIL_CONFIG['manager_recipient']]

        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
            server.sendmail(EMAIL_CONFIG['sender'], recipients, msg.as_string())

        logger.info(f"Email sent successfully to {recipients}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")


# ----------------- GIT -----------------
def setup_repository(repo_url, branch_name):
    """Clone or update repository using GitPython"""
    logger.info(f"Setting up repository: {repo_url}, branch: {branch_name}")

    # Load PAT from env (fallback to hardcoded)
    pat = os.getenv(
        "GITHUB_PAT",
        "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"
    )

    if repo_url.startswith("https://"):
        repo_url_with_auth = repo_url.replace("https://", f"https://{pat}@")
        logger.info("Added authentication to repo URL")
    else:
        repo_url_with_auth = repo_url

    repo_name = repo_url.split('/')[-1].replace('.git', '')
    repo_path = os.path.join(os.getcwd(), repo_name)
    logger.info(f"Repository will be cloned to: {repo_path}")

    try:
        if not os.path.exists(repo_path):
            logger.info(f"Cloning repository with depth=1: {repo_url_with_auth}")
            start_time = time.time()

            # Clone with depth=1 for faster cloning (shallow clone)
            repo = Repo.clone_from(
                repo_url_with_auth,
                repo_path,
                branch=branch_name,
                depth=1
            )

            clone_time = time.time() - start_time
            logger.info(f"Repository cloned successfully in {clone_time:.2f} seconds")
        else:
            logger.info("Repository already exists, pulling latest changes")
            repo = Repo(repo_path)
            origin = repo.remotes.origin

            # Stash any local changes before pulling
            try:
                repo.git.stash()
                logger.info("Stashed any local changes")
            except Exception:
                logger.info("No local changes to stash")

            # Fetch and pull latest changes
            start_time = time.time()
            origin.fetch()
            repo.git.checkout(branch_name)
            origin.pull(branch_name)
            pull_time = time.time() - start_time
            logger.info(f"Repository updated successfully in {pull_time:.2f} seconds")

        # Verify the current branch
        current_branch = repo.active_branch.name
        logger.info(f"Current branch: {current_branch}")

        # Get the latest commit
        latest_commit = repo.head.commit.hexsha
        logger.info(f"Latest commit: {latest_commit[:8]}")

        logger.info(f"Repository ready at {repo_path}")
        return repo_path

    except GitCommandError as e:
        logger.error(f"Repository setup failed: {e}")
        # Clean up if cloning failed
        if os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path)
                logger.info(f"Cleaned up failed repository at {repo_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up repository: {cleanup_error}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in repository setup: {e}")
        return None


def get_changed_files(repo_path, commit_id):
    """Get changed Python files using GitPython"""
    logger.info(f"Getting changed files for commit: {commit_id}")
    try:
        repo = Repo(repo_path)

        # For shallow clones, we need to handle the case where parent commits might not be available
        try:
            commit = repo.commit(commit_id)
            logger.info(f"Found commit: {commit.summary}")

            if not commit.parents:  # First commit or shallow clone
                logger.info("This appears to be the first commit or a shallow clone")
                # In shallow clones, we can't get diff with parent, so check all Python files
                changed_files = [item.path for item in commit.tree.traverse()
                                 if item.path.endswith('.py')]
            else:
                logger.info(f"Comparing with parent commit: {commit.parents[0].hexsha[:8]}")
                diff = commit.parents[0].diff(commit)
                changed_files = [item.a_path for item in diff
                                 if item.a_path and item.a_path.endswith('.py')]
        except Exception:
            # Fallback for shallow clones where we can't access parent commits
            logger.info("Using fallback method to get changed files (shallow clone detected)")
            changed_files = []
            for root, dirs, files in os.walk(repo_path):
                for file in files:
                    if file.endswith('.py'):
                        rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                        changed_files.append(rel_path)

        logger.info(f"Found {len(changed_files)} changed Python files: {changed_files}")
        return changed_files
    except Exception as e:
        logger.error(f"Error getting changed files: {e}")
        return []


# ----------------- CODE CHECKS -----------------
def parse_issues(output, tool_name, filename):
    """Parse tool output and extract structured issue information"""
    issues = []
    lines = output.strip().split('\n')
    pylint_score = None

    for line in lines:
        if not line.strip():
            continue

        if "Your code has been rated at" in line:
            # Pylint score line
            match = re.search(r"rated at ([\d.]+)/10", line)
            if match:
                pylint_score = float(match.group(1))
            continue

        if tool_name == 'pylint':
            # Pylint format: filename:line:column: [code] message
            match = re.match(r'(.+?):(\d+):(\d+): (\w+):? (.+)', line)
            if match:
                issues.append({
                    'file': match.group(1),
                    'line': match.group(2),
                    'column': match.group(3),
                    'code': match.group(4),
                    'message': match.group(5),
                    'tool': 'Pylint'
                })

        elif tool_name == 'black':
            # Black format: would reformat filename
            if 'would reformat' in line:
                issues.append({
                    'file': filename if filename else 'multiple files',
                    'message': 'File needs formatting',
                    'tool': 'Black'
                })

    return issues, pylint_score


def deduplicate_issues(issues):
    """Remove duplicate issues across different tools"""
    unique_issues = []
    seen_issues = set()

    for issue in issues:
        # Create a unique identifier for each issue
        issue_id = f"{issue['file']}:{issue.get('line', '')}:{issue.get('message', '')}"

        if issue_id not in seen_issues:
            seen_issues.add(issue_id)
            unique_issues.append(issue)

    return unique_issues


def run_code_checks(files, repo_path):
    """Run code quality checks with pylint and black"""
    logger.info(f"Running code checks on {len(files)} files in {repo_path}")
    all_issues = []
    pylint_scores = []
    original_dir = os.getcwd()

    try:
        os.chdir(repo_path)
        logger.info(f"Changed working directory to: {os.getcwd()}")

        # Check if files exist
        existing_files = [f for f in files if os.path.exists(f)]
        if len(existing_files) != len(files):
            missing_files = set(files) - set(existing_files)
            logger.warning(f"Some files don't exist: {missing_files}")

        # Run pylint on all files at once for a single score
        if existing_files:
            try:
                logger.info(f"Running pylint on {len(existing_files)} files")
                pylint_args = [
                                  'pylint',
                                  '--disable=C0301',  # Disable line-too-long errors
                                  '--max-line-length=120'  # Increase line length limit if needed
                              ] + existing_files

                result = subprocess.run(
                    pylint_args,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                pylint_issues, pylint_score = parse_issues(result.stdout, 'pylint', None)
                all_issues.extend(pylint_issues)
                pylint_scores.append(pylint_score)
                if pylint_issues:
                    logger.warning(f"Pylint found {len(pylint_issues)} issues")
                else:
                    logger.info("Pylint check passed")
            except subprocess.TimeoutExpired:
                logger.error("Pylint timed out")
            except Exception as e:
                logger.error(f"Error running pylint: {e}")

        # Run black check
        if existing_files:
            try:
                logger.info(f"Running black on {len(existing_files)} files")
                result = subprocess.run(
                    ['black', '--check'] + existing_files,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    black_issues, _ = parse_issues(result.stderr or result.stdout, 'black', None)
                    all_issues.extend(black_issues)
                    logger.warning(f"Black found {len(black_issues)} formatting issues")
                else:
                    logger.info("Black formatting check passed")
            except subprocess.TimeoutExpired:
                logger.error("Black check timed out")
            except Exception as e:
                logger.error(f"Error running black: {e}")
        else:
            logger.info("No existing files to run black on")

    except Exception as e:
        logger.error(f"Unexpected error in code checks: {e}")
    finally:
        os.chdir(original_dir)
        logger.info(f"Restored working directory to: {original_dir}")

    # Deduplicate issues
    unique_issues = deduplicate_issues(all_issues)
    logger.info(f"Code checks completed with {len(unique_issues)} unique issues found")

    # Calculate average pylint score
    avg_pylint_score = sum(pylint_scores) / len(pylint_scores) if pylint_scores else None

    return unique_issues, avg_pylint_score


# ----------------- WEBHOOK -----------------
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        logger.info("=" * 50)
        logger.info("Webhook received")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"JSON payload: {request.json}")

        # Run in background thread
        Thread(target=process_webhook, args=(request.json,)).start()

        # Respond quickly to GitHub
        logger.info("Webhook accepted, processing in background")
        return jsonify({"status": "accepted", "message": "Webhook is being processed"}), 202

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def process_webhook(data):
    """Background job: clone repo, check code, send email"""
    process_id = int(time.time() * 1000)
    logger.info(f"[{process_id}] Starting webhook processing")
    employee_email = data['head_commit']['author'].get('email')
    try:
        repo_url, branch_name, commit_id = None, None, None

        if 'check_suite' in data:
            logger.info(f"[{process_id}] Processing check_suite payload")
            check_suite = data['check_suite']
            commit_id = check_suite.get('head_sha')
            branch_name = check_suite.get('head_branch')
            try:
                repo_url = check_suite['pull_requests'][0]['head']['repo']['clone_url']
                logger.info(f"[{process_id}] Found repo URL in check_suite: {repo_url}")
            except (KeyError, IndexError):
                logger.error(f"[{process_id}] check_suite payload missing repo URL")
                return

        elif 'repository' in data and 'ref' in data and 'after' in data:
            logger.info(f"[{process_id}] Processing push payload")
            repo_url = data['repository']['clone_url']
            branch_name = data['ref'].split('/')[-1]
            commit_id = data['after']
            logger.info(f"[{process_id}] Found repo URL: {repo_url}, branch: {branch_name}, "
                        f"commit: {commit_id}")

        if not repo_url or not branch_name or not commit_id:
            logger.error(f"[{process_id}] Invalid webhook payload - missing required fields")
            return

        logger.info(f"[{process_id}] Processing repo={repo_url}, branch={branch_name}, "
                    f"commit={commit_id}")

        repo_path = setup_repository(repo_url, branch_name)
        if not repo_path:
            logger.error(f"[{process_id}] Failed to setup repository")
            send_email(
                f"Repository Setup Failed - {repo_url.split('/')[-1]}",
                repo_url.split('/')[-1],
                commit_id,
                [],
                repo_url,
                branch_name,
                employee_email=employee_email
            )
            return

        changed_files = get_changed_files(repo_path, commit_id)
        if not changed_files:
            logger.info(f"[{process_id}] No Python files changed in this commit")
            send_email(
                f"No Python Changes - {repo_url.split('/')[-1]}",
                repo_url.split('/')[-1],
                commit_id,
                [],
                repo_url,
                branch_name,
                employee_email=employee_email
            )
            return

        issues, pylint_score = run_code_checks(changed_files, repo_path)

        repo_name = repo_url.split('/')[-1]
        subject = f"Code Quality Report - {repo_name} - {'Issues Found' if issues else 'All Checks Passed'}"
        send_email(subject, repo_name, commit_id, issues, repo_url, branch_name, pylint_score, employee_email=employee_email)

        if issues:
            logger.warning(f"[{process_id}] {len(issues)} issues found")
        else:
            logger.info(f"[{process_id}] All checks passed ✅")

    except Exception as e:
        logger.exception(f"[{process_id}] Unexpected error in process_webhook: {e}")
        send_email(
            "Webhook Processing Error",
            "Unknown",
            "N/A",
            [{'file': 'System', 'message': str(e), 'tool': 'System'}],
            "N/A",
            "N/A",
            employee_email=employee_email
        )
    finally:
        logger.info(f"[{process_id}] Webhook processing completed")
        logger.info("=" * 50)


# ----------------- START APP -----------------
if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, host='0.0.0.0', port=5000)
