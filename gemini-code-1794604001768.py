from flask import Flask, request, jsonify
from flask_cors import CORS
import instaloader
import re
import os

app = Flask(__name__)
CORS(app)

L = instaloader.Instaloader()

# Optional: Stories ke liye agar login session file ho toh load kar sakte hain
# if os.path.exists("session-file"):
#     L.load_session_from_file("YOUR_USERNAME", filename="session-file")

def extract_shortcode(url):
    match = re.search(r'/(p|reel|tv)/([A-Za-z0-9_-]+)', url)
    return match.group(2) if match else None

@app.route('/api/download', methods=['POST'])
def download_all():
    data = request.json
    input_val = data.get('url', '').strip()
    mode = data.get('mode', 'post') # 'post', 'story', 'dp'

    if not input_val:
        return jsonify({'error': 'Please enter a valid link or username'}), 400

    try:
        # 1. Profile Picture (DP) Downloader
        if mode == 'dp':
            username = input_val.split('/')[-1] if 'instagram.com' in input_val else input_val
            username = username.replace('@', '').split('?')[0]
            profile = instaloader.Profile.from_username(L.context, username)
            return jsonify({
                'status': 'success',
                'type': 'dp',
                'username': profile.username,
                'media_url': profile.profile_pic_url
            })

        # 2. Post / Reel Downloader
        elif mode == 'post':
            shortcode = extract_shortcode(input_val)
            if not shortcode:
                return jsonify({'error': 'Invalid Post or Reel URL'}), 400
            
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            media_items = []

            if post.typename == 'GraphSidecar':
                for node in post.get_sidecar_nodes():
                    media_items.append({
                        'is_video': node.is_video,
                        'url': node.video_url if node.is_video else node.display_url
                    })
            else:
                media_items.append({
                    'is_video': post.is_video,
                    'url': post.video_url if post.is_video else post.url
                })

            return jsonify({
                'status': 'success',
                'type': 'post',
                'caption': post.caption if post.caption else '',
                'media': media_items
            })

        # 3. Stories Downloader
        elif mode == 'story':
            username = input_val.split('/')[-1] if 'instagram.com' in input_val else input_val
            username = username.replace('@', '').split('?')[0]
            profile = instaloader.Profile.from_username(L.context, username)
            
            stories_data = []
            for story in L.get_stories(userids=[profile.userid]):
                for item in story.get_items():
                    stories_data.append({
                        'is_video': item.is_video,
                        'url': item.video_url if item.is_video else item.url
                    })
            
            if not stories_data:
                return jsonify({'error': 'No active stories found or account is private / login required.'}), 404

            return jsonify({
                'status': 'success',
                'type': 'story',
                'media': stories_data
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)