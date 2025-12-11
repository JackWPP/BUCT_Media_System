"""
Test photo upload functionality
"""
import requests
import os
from io import BytesIO
from PIL import Image

# API base URL
BASE_URL = "http://127.0.0.1:8002/api/v1"

# Admin credentials
ADMIN_EMAIL = "admin@buct.edu.cn"
ADMIN_PASSWORD = "admin123"


def create_test_image():
    """Create a test image in memory"""
    # Create a simple 800x600 RGB image
    img = Image.new('RGB', (800, 600), color=(73, 109, 137))
    
    # Save to BytesIO
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes


def login():
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✓ Login successful")
        return token
    else:
        print(f"✗ Login failed: {response.status_code}")
        print(response.text)
        return None


def upload_photo(token):
    """Upload a test photo"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Create test image
    test_image = create_test_image()
    
    # Prepare files and data
    files = {
        'file': ('test_photo.jpg', test_image, 'image/jpeg')
    }
    
    data = {
        'description': 'This is a test photo',
        'season': 'Spring',
        'category': 'Landscape'
    }
    
    response = requests.post(
        f"{BASE_URL}/photos/upload",
        headers=headers,
        files=files,
        data=data
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✓ Photo uploaded successfully")
        print(f"  Photo ID: {result['id']}")
        print(f"  Filename: {result['filename']}")
        print(f"  Dimensions: {result['width']}x{result['height']}")
        print(f"  Thumbnail: {result['thumb_path']}")
        return result['id']
    else:
        print(f"✗ Photo upload failed: {response.status_code}")
        print(response.text)
        return None


def list_photos(token):
    """List all photos"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/photos",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Photos listed successfully")
        print(f"  Total: {result['total']}")
        print(f"  Page: {result['page']}")
        print(f"  Items: {len(result['items'])}")
        return result['items']
    else:
        print(f"✗ List photos failed: {response.status_code}")
        print(response.text)
        return None


def get_photo(token, photo_id):
    """Get a specific photo"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/photos/{photo_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Photo retrieved successfully")
        print(f"  ID: {result['id']}")
        print(f"  Filename: {result['filename']}")
        print(f"  Description: {result['description']}")
        print(f"  Season: {result['season']}")
        print(f"  Category: {result['category']}")
        return result
    else:
        print(f"✗ Get photo failed: {response.status_code}")
        print(response.text)
        return None


def main():
    """Main test flow"""
    print("=" * 60)
    print("Testing Photo Upload API")
    print("=" * 60)
    
    # Step 1: Login
    print("\n[1] Logging in...")
    token = login()
    if not token:
        return
    
    # Step 2: Upload photo
    print("\n[2] Uploading photo...")
    photo_id = upload_photo(token)
    if not photo_id:
        return
    
    # Step 3: Get photo details
    print("\n[3] Getting photo details...")
    photo = get_photo(token, photo_id)
    
    # Step 4: List photos
    print("\n[4] Listing all photos...")
    photos = list_photos(token)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
