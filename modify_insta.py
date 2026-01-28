# Read the current insta.py file and add profile picture download functionality
with open('insta.py', 'r') as f:
    content = f.read()

# Check if the function already exists
if 'download_profile_picture' in content:
    print('Function already exists')
else:
    print('Function does not exist, adding it')
    
    # Find the end of the file to add the new function
    lines = content.split('\n')
    
    # Find the last function definition
    last_func_line = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('def ') and 'print_usage' in line:
            last_func_line = i
            break
    
    # Add the new function after the last function
    new_function = '''
def download_profile_picture(api_client, username):
    """Download profile picture of a user"""
    try:
        uname = username.lstrip("@")
        user_info = api_client.user_info_by_username(uname)
        
        # Get the profile picture URL
        profile_pic_url = user_info.profile_pic_url_hd
        
        # Create download directory
        out_dir = get_user_download_path("profile_pictures", uname)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Download the profile picture
        import requests
        response = requests.get(profile_pic_url)
        if response.status_code == 200:
            filename = str(out_dir / f"{uname}_profile.jpg")
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ Profile picture downloaded to: {filename}")
            return True
        else:
            print(f"✗ Failed to download profile picture for {uname}")
            return False
    except Exception as e:
        print(f"✗ Profile picture download failed for {username}: {e}")
        return False

'''
    
    # Insert the new function before the print_usage function
    lines.insert(last_func_line, new_function)
    
    # Update the command parser to include the new command
    # Find the try_parse_and_execute_commands function
    command_parser_line = 0
    for i, line in enumerate(lines):
        if 'def try_parse_and_execute_commands' in line:
            command_parser_line = i
            break
    
    # Add the new command to the parser
    if command_parser_line > 0:
        # Find the end of the function
        end_line = command_parser_line
        for i in range(command_parser_line, len(lines)):
            if lines[i].strip() == 'return False' and 'try_parse_and_execute_commands' in ''.join(lines[max(0, i-10):i]):
                end_line = i
                break
        
        # Add the new command before the return statement
        new_command = '    # Profile picture download\n    m = re.search(r"download profile picture of @([A-Za-z0-9._]+)$", t, flags=re.IGNORECASE)\n    if m:\n        username = m.group(1)\n        download_profile_picture(api_client, username)\n        return True\n\n'
        lines.insert(end_line, new_command)
    
    # Write the updated content back to the file
    with open('insta.py', 'w') as f:
        f.write('\n'.join(lines))
    
    print('Profile picture download functionality added')