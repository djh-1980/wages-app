#!/usr/bin/env python3
"""
CDN Version Checker and Updater
Automatically checks for updates to CDN libraries and can update base.html
"""

import json
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class CDNVersionChecker:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.template_path = self.base_dir / 'templates' / 'base.html'
        self.config_path = self.base_dir / 'config' / 'cdn_versions.json'
        
        # CDN library configurations
        self.libraries = {
            'bootstrap': {
                'name': 'Bootstrap',
                'current_pattern': r'bootstrap@([\d.]+)/dist/css/bootstrap\.min\.css',
                'cdn_url': 'https://cdn.jsdelivr.net/npm/bootstrap@{version}/dist/css/bootstrap.min.css',
                'js_url': 'https://cdn.jsdelivr.net/npm/bootstrap@{version}/dist/js/bootstrap.bundle.min.js',
                'api_url': 'https://registry.npmjs.org/bootstrap/latest',
                'version_key': 'version'
            },
            'bootstrap-icons': {
                'name': 'Bootstrap Icons',
                'current_pattern': r'bootstrap-icons@([\d.]+)/font/bootstrap-icons\.css',
                'cdn_url': 'https://cdn.jsdelivr.net/npm/bootstrap-icons@{version}/font/bootstrap-icons.css',
                'api_url': 'https://registry.npmjs.org/bootstrap-icons/latest',
                'version_key': 'version'
            },
            'chartjs': {
                'name': 'Chart.js',
                'current_pattern': r'chart\.js@([\d.]+)/dist/chart\.umd\.js',
                'cdn_url': 'https://cdn.jsdelivr.net/npm/chart.js@{version}/dist/chart.umd.js',
                'api_url': 'https://registry.npmjs.org/chart.js/latest',
                'version_key': 'version'
            },
            'jspdf': {
                'name': 'jsPDF',
                'current_pattern': r'jspdf/([\d.]+)/jspdf\.umd\.min\.js',
                'cdn_url': 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/{version}/jspdf.umd.min.js',
                'api_url': 'https://api.cdnjs.com/libraries/jspdf',
                'version_key': 'version'
            },
            'jspdf-autotable': {
                'name': 'jsPDF-AutoTable',
                'current_pattern': r'jspdf-autotable/([\d.]+)/jspdf\.plugin\.autotable\.min\.js',
                'cdn_url': 'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/{version}/jspdf.plugin.autotable.min.js',
                'api_url': 'https://api.cdnjs.com/libraries/jspdf-autotable',
                'version_key': 'version'
            }
        }

    def get_current_versions(self) -> Dict[str, str]:
        """Extract current versions from base.html"""
        versions = {}
        
        if not self.template_path.exists():
            return versions
            
        content = self.template_path.read_text()
        
        for lib_id, lib_config in self.libraries.items():
            pattern = lib_config['current_pattern']
            match = re.search(pattern, content)
            if match:
                versions[lib_id] = match.group(1)
        
        return versions

    def get_latest_version(self, lib_id: str) -> str:
        """Fetch latest version from CDN API"""
        lib_config = self.libraries[lib_id]
        
        try:
            response = requests.get(lib_config['api_url'], timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Handle different API response formats
            if lib_id in ['jspdf', 'jspdf-autotable']:
                # CDNJS API format
                return data.get('version', '')
            else:
                # NPM registry format
                return data.get('version', '')
                
        except Exception as e:
            print(f"Error fetching latest version for {lib_config['name']}: {e}")
            return ''

    def check_all_versions(self) -> Dict[str, Dict[str, str]]:
        """Check all libraries for updates"""
        current_versions = self.get_current_versions()
        results = {}
        
        for lib_id in self.libraries.keys():
            current = current_versions.get(lib_id, 'Unknown')
            latest = self.get_latest_version(lib_id)
            
            results[lib_id] = {
                'name': self.libraries[lib_id]['name'],
                'current': current,
                'latest': latest,
                'update_available': latest and current != latest and self._compare_versions(current, latest) < 0
            }
        
        return results

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            
            if len(parts1) < len(parts2):
                return -1
            elif len(parts1) > len(parts2):
                return 1
            
            return 0
        except:
            return 0

    def update_library(self, lib_id: str, new_version: str) -> bool:
        """Update a specific library to a new version"""
        if not self.template_path.exists():
            return False
        
        # Create backup
        backup_path = self.template_path.with_suffix('.html.bak')
        self.template_path.rename(backup_path)
        
        try:
            content = backup_path.read_text()
            lib_config = self.libraries[lib_id]
            
            # Update CSS/main URL
            old_pattern = lib_config['current_pattern']
            
            if lib_id == 'bootstrap':
                # Update both CSS and JS
                content = re.sub(
                    r'bootstrap@[\d.]+/dist/css/bootstrap\.min\.css',
                    f'bootstrap@{new_version}/dist/css/bootstrap.min.css',
                    content
                )
                content = re.sub(
                    r'bootstrap@[\d.]+/dist/js/bootstrap\.bundle\.min\.js',
                    f'bootstrap@{new_version}/dist/js/bootstrap.bundle.min.js',
                    content
                )
            elif lib_id == 'bootstrap-icons':
                content = re.sub(
                    r'bootstrap-icons@[\d.]+/font/bootstrap-icons\.css',
                    f'bootstrap-icons@{new_version}/font/bootstrap-icons.css',
                    content
                )
            elif lib_id == 'chartjs':
                content = re.sub(
                    r'chart\.js@[\d.]+/dist/chart\.umd\.js',
                    f'chart.js@{new_version}/dist/chart.umd.js',
                    content
                )
            elif lib_id == 'jspdf':
                content = re.sub(
                    r'jspdf/[\d.]+/jspdf\.umd\.min\.js',
                    f'jspdf/{new_version}/jspdf.umd.min.js',
                    content
                )
            elif lib_id == 'jspdf-autotable':
                content = re.sub(
                    r'jspdf-autotable/[\d.]+/jspdf\.plugin\.autotable\.min\.js',
                    f'jspdf-autotable/{new_version}/jspdf.plugin.autotable.min.js',
                    content
                )
            
            # Write updated content
            self.template_path.write_text(content)
            
            # Remove backup on success
            backup_path.unlink()
            return True
            
        except Exception as e:
            print(f"Error updating {lib_id}: {e}")
            # Restore backup
            if backup_path.exists():
                backup_path.rename(self.template_path)
            return False

    def update_all_libraries(self, versions_to_update: Dict[str, str]) -> Dict[str, bool]:
        """Update multiple libraries at once"""
        results = {}
        
        for lib_id, new_version in versions_to_update.items():
            results[lib_id] = self.update_library(lib_id, new_version)
        
        return results

    def save_version_check(self, results: Dict):
        """Save version check results to config file"""
        self.config_path.parent.mkdir(exist_ok=True)
        
        data = {
            'last_check': datetime.now().isoformat(),
            'libraries': results
        }
        
        self.config_path.write_text(json.dumps(data, indent=2))

    def load_version_check(self) -> Dict:
        """Load last version check results"""
        if not self.config_path.exists():
            return {}
        
        try:
            return json.loads(self.config_path.read_text())
        except:
            return {}


def main():
    """CLI interface for CDN version checker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check and update CDN library versions')
    parser.add_argument('--check', action='store_true', help='Check for updates')
    parser.add_argument('--update', nargs='+', help='Update specific libraries (e.g., bootstrap chartjs)')
    parser.add_argument('--update-all', action='store_true', help='Update all libraries with available updates')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    checker = CDNVersionChecker()
    
    if args.check or not any([args.update, args.update_all]):
        # Check for updates
        results = checker.check_all_versions()
        checker.save_version_check(results)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n📦 CDN Library Version Check\n")
            print(f"{'Library':<20} {'Current':<12} {'Latest':<12} {'Status'}")
            print("-" * 60)
            
            for lib_id, info in results.items():
                status = "⚠️  Update Available" if info['update_available'] else "✅ Up to date"
                print(f"{info['name']:<20} {info['current']:<12} {info['latest']:<12} {status}")
            
            print()
    
    elif args.update:
        # Update specific libraries
        current_versions = checker.get_current_versions()
        updates = {}
        
        for lib_id in args.update:
            if lib_id in checker.libraries:
                latest = checker.get_latest_version(lib_id)
                if latest:
                    updates[lib_id] = latest
        
        if updates:
            print(f"\n🔄 Updating {len(updates)} libraries...\n")
            results = checker.update_all_libraries(updates)
            
            for lib_id, success in results.items():
                status = "✅ Success" if success else "❌ Failed"
                print(f"{checker.libraries[lib_id]['name']}: {status}")
            print()
    
    elif args.update_all:
        # Update all libraries with available updates
        results = checker.check_all_versions()
        updates = {
            lib_id: info['latest'] 
            for lib_id, info in results.items() 
            if info['update_available']
        }
        
        if updates:
            print(f"\n🔄 Updating {len(updates)} libraries...\n")
            update_results = checker.update_all_libraries(updates)
            
            for lib_id, success in update_results.items():
                status = "✅ Success" if success else "❌ Failed"
                print(f"{checker.libraries[lib_id]['name']}: {status}")
            print()
        else:
            print("\n✅ All libraries are up to date!\n")


if __name__ == '__main__':
    main()
