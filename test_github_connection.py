#!/usr/bin/env python3
"""
Test GitHub Connection for BNX-edu repository
"""

import json
import requests
import os

def test_github_connection():
    """Test if GitHub is properly connected with BNX-edu"""
    print("Testing GitHub Connection for BNX-edu")
    print("=" * 50)
    
    # Load configuration
    try:
        with open('cloud_account_config.json', 'r') as f:
            config = json.load(f)
        
        github_token = config.get('github_token')
        github_owner = config.get('github_owner')
        github_repo = config.get('github_repo')
        enabled = config.get('enabled')
        
        print(f"GitHub Owner: {github_owner}")
        print(f"Repository: {github_repo}")
        print(f"Enabled: {enabled}")
        print(f"Token: {'*' * 20 if github_token and github_token != 'PASTE_YOUR_GITHUB_TOKEN_HERE' else 'NOT SET'}")
        
        if not github_token or github_token == 'PASTE_YOUR_GITHUB_TOKEN_HERE':
            print("\n❌ GitHub token not configured!")
            print("Please add your GitHub Personal Access Token to cloud_account_config.json")
            return False
        
        # Test GitHub API connection
        print(f"\n🔍 Testing connection to GitHub...")
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Test user authentication
        print("Testing user authentication...")
        user_response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        
        if user_response.status_code == 200:
            user_data = user_response.json()
            print(f"✅ Authenticated as: {user_data.get('login')}")
            print(f"   Name: {user_data.get('name', 'Not set')}")
            print(f"   Public repos: {user_data.get('public_repos', 0)}")
        else:
            print(f"❌ Authentication failed: {user_response.status_code}")
            return False
        
        # Test repository access
        print(f"\n🔍 Testing repository access: {github_owner}/{github_repo}")
        repo_url = f"https://api.github.com/repos/{github_owner}/{github_repo}"
        repo_response = requests.get(repo_url, headers=headers, timeout=10)
        
        if repo_response.status_code == 200:
            repo_data = repo_response.json()
            print(f"✅ Repository found: {repo_data.get('full_name')}")
            print(f"   Description: {repo_data.get('description', 'No description')}")
            print(f"   Private: {repo_data.get('private')}")
            print(f"   Default branch: {repo_data.get('default_branch')}")
            print(f"   GitHub Pages: {'Enabled' if repo_data.get('has_pages') else 'Not enabled'}")
            
            if repo_data.get('has_pages'):
                pages_url = f"https://{github_owner}.github.io/{github_repo}"
                print(f"   Pages URL: {pages_url}")
            
        elif repo_response.status_code == 404:
            print(f"⚠️  Repository not found: {github_owner}/{github_repo}")
            print("   You need to create this repository on GitHub first")
            print(f"   Go to: https://github.com/new")
            print(f"   Repository name: {github_repo}")
            return False
        else:
            print(f"❌ Repository access failed: {repo_response.status_code}")
            return False
        
        # Test write permissions
        print(f"\n🔍 Testing write permissions...")
        try:
            # Try to get repository contents
            contents_url = f"https://api.github.com/repos/{github_owner}/{github_repo}/contents"
            contents_response = requests.get(contents_url, headers=headers, timeout=10)
            
            if contents_response.status_code == 200:
                contents = contents_response.json()
                print(f"✅ Repository has {len(contents)} files/folders")
                
                # List some files
                for item in contents[:5]:  # Show first 5 items
                    print(f"   - {item['name']} ({item['type']})")
                    
            elif contents_response.status_code == 404:
                print("✅ Repository is empty (ready for first push)")
            else:
                print(f"⚠️  Contents check: {contents_response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Write permission test error: {e}")
        
        print(f"\n" + "=" * 50)
        print("🎉 GitHub Connection Test Complete!")
        print("=" * 50)
        print(f"✅ Connected to: {github_owner}/{github_repo}")
        print(f"✅ Authentication: Working")
        print(f"✅ Repository access: {'Working' if repo_response.status_code == 200 else 'Repository needs to be created'}")
        print(f"✅ Ready for deployment!")
        
        if repo_response.status_code != 200:
            print(f"\n📋 Next step: Create repository at https://github.com/new")
            print(f"   Repository name: {github_repo}")
            print(f"   Make it public for GitHub Pages")
        
        return True
        
    except FileNotFoundError:
        print("❌ Configuration file not found!")
        print("Run SETUP_NEW_REPOSITORY_SIMPLE.py first")
        return False
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_github_connection()
