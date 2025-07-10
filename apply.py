import os
from pathlib import Path
from typing import Final

import requests
from environs import Env
from requests import Response

# abs path
ABS_PATH: Final[Path] = Path(__file__).resolve().parent

# loading env
env = Env()
env.read_env(ABS_PATH / ".env")

# constants
REPO: Final[str] = "python-boilerplate/features-database"
BRANCH: Final[str] = "main"
FEATURES_DIR: Final[str] = "features"
API_URL: Final[str] = f"https://api.github.com/repos/{REPO}/contents/{FEATURES_DIR}?ref={BRANCH}"
API_FEATURE_CONTENT_URL: Final[
    str] = f"https://api.github.com/repos/{REPO}/contents/{FEATURES_DIR}/{{feature}}?ref={BRANCH}"
RAW_URL: Final[str] = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{FEATURES_DIR}"
GITHUB_TOKEN: Final[str] = env.str("GITHUB_API_TOKEN")
HEADERS: Final[dict[str, str] | None] = {
    "Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else None


def fetch_available_features() -> list[str]:
    """Fetch the list of available features from the GitHub repository.

    Makes a GET request to the GitHub API to retrieve all available features
    from the features directory of the specified repository.

    Returns:
        list[str]: A list of feature names available in the repository.

    Raises:
        requests.exceptions.HTTPError: If the API request fails.
        requests.exceptions.RequestException: If there's a network error.
    """
    response: Response = requests.get(API_URL, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    features = [feature["name"] for feature in data]

    return features


def fetch_feature_files(feature_name: str) -> list[str]:
    """List all files in a feature directory recursively.

    Retrieves all files within a specific feature directory from the GitHub
    repository. If subdirectories are found, it recursively fetches files
    from those subdirectories as well.

    Args:
        feature_name (str): The name of the feature directory to list files from.
                           Can include subdirectory paths separated by forward slashes.

    Returns:
        list[str]: A list of file paths relative to the feature directory.
                  Subdirectory files include the subdirectory path prefix.

    Raises:
        requests.exceptions.HTTPError: If the API request fails.
        requests.exceptions.RequestException: If there's a network error.
    """
    response: Response = requests.get(
        API_FEATURE_CONTENT_URL.format(feature=feature_name), headers=HEADERS
    )
    response.raise_for_status()
    data = response.json()
    files: list[str] = []
    for item in data:
        if item["type"] == "file":
            files.append(item["name"])
        if item["type"] == "dir":
            # If it's a directory, we can recursively list files in it
            sub_files: list[str] = fetch_feature_files(
                f"{feature_name}/{item['name']}")
            files.extend(
                [f"{item['name']}/{sub_file}" for sub_file in sub_files])
    return files


def download_feature_file(url: str, path: Path) -> None:
    """Download a file from a URL and save it to the specified path.

    Downloads a file from the given URL and writes its content to the
    specified local file path. Creates parent directories if they don't exist.
    Prints a success message upon completion.

    Args:
        url (str): The URL of the file to download.
        path (Path): The local file path where the downloaded file will be saved.

    Returns:
        None

    Raises:
        requests.exceptions.HTTPError: If the download request fails.
        requests.exceptions.RequestException: If there's a network error.
        OSError: If there's an error writing to the file system.
    """
    response: Response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    with open(path, "wb") as file:
        file.write(response.content)
    print(f"File successfully downloaded: {path}")


def display_available_features(features: list[str]) -> None:
    """Display all available features and their files."""
    print("Available features:\n")
    for idx, feature in enumerate(features):
        print(f"{idx + 1}: {feature}")
        try:
            feature_files = fetch_feature_files(feature_name=feature)
            print(f"Feature files: {feature_files}")
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not list files for {feature}: {e}")


def get_user_feature_selection(features: list[str]) -> list[str]:
    """Get and validate user's feature selection."""
    selected = input(
        "\nEnter the number of the feature you want to apply using comma \
        (or 'all' to apply all features): "
    )

    if selected.lower().strip() == 'all':
        return features

    try:
        indices = [int(x.strip())-1 for x in selected.split(",")]
        # Validate indices
        for idx in indices:
            if idx < 0 or idx >= len(features):
                raise ValueError(
                    f"Invalid feature number: {idx + 1}. Valid range: 1-{len(features)}")
        return [features[i] for i in indices]
    except ValueError as e:
        print(f"Error: Invalid input - {e}")
        print("Please enter comma-separated numbers or 'all'")
        return []


def setup_target_directory() -> str:
    """Get target directory from user and create it."""
    target_dir = input(
        "In which directory should the files be downloaded? (Enter = current):"
    ).strip() or "."

    try:
        os.makedirs(target_dir, exist_ok=True)
        print(f"Target directory: {os.path.abspath(target_dir)}")
        return target_dir
    except OSError as e:
        print(f"Error: Could not create directory '{target_dir}': {e}")
        return ""


def download_feature_files(
    chosen_features: list[str],
    target_dir: str
) -> tuple[int, int]:
    """Download files for selected features and return download statistics."""
    total_files = 0
    successful_downloads = 0

    for feature in chosen_features:
        print(f"\nProcessing feature: {feature}")
        try:
            feature_files = fetch_feature_files(feature_name=feature)
            for file in feature_files:
                total_files += 1
                try:
                    file_url = f"{RAW_URL}/{feature}/{file}"
                    file_path = Path(target_dir) / file

                    # Create parent directories if needed
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    download_feature_file(url=file_url, path=file_path)
                    successful_downloads += 1
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading {file}: {e}")
                except OSError as e:
                    print(f"Error saving {file}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Error processing feature {feature}: {e}")

    return total_files, successful_downloads


def display_summary(total_files: int, successful_downloads: int) -> None:
    """Display download operation summary."""
    print(f"\n{'='*50}")
    print("Download Summary:")
    print(f"Total files: {total_files}")
    print(f"Successfully downloaded: {successful_downloads}")
    print(f"Failed downloads: {total_files - successful_downloads}")

    if successful_downloads == total_files and total_files > 0:
        print("\nAll selected features have been applied successfully!")
    elif successful_downloads > 0:
        print(
            f"\nPartially completed: {successful_downloads}/{total_files} files downloaded.")
    else:
        print("\nNo files were downloaded. Please check your connection and try again.")


def main() -> None:
    """Main function to fetch and apply features."""
    try:
        # Fetch available features
        print("Fetching available features...")
        features = fetch_available_features()

        # Display features and their files
        display_available_features(features)

        # Get user selection
        chosen_features = get_user_feature_selection(features)
        if not chosen_features:
            return

        # Setup target directory
        target_dir = setup_target_directory()
        if not target_dir:
            return

        # Download selected feature files
        total_files, successful_downloads = download_feature_files(
            chosen_features, target_dir
        )

        # Display operation summary
        display_summary(total_files, successful_downloads)

    except requests.exceptions.RequestException as e:
        print(f"Error: Could not connect to GitHub API: {e}")
        print("Please check your internet connection and GitHub token.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Please try again or report this issue.")


if __name__ == "__main__":
    main()
