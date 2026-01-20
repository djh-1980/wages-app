#!/usr/bin/env python3
"""
Python Dependency Version Checker and Updater
Automatically checks for updates to Python packages in requirements.txt
"""

import json
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import subprocess

class PythonDependencyChecker:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.requirements_path = self.base_dir / 'requirements.txt'
        self.config_path = self.base_dir / 'config' / 'python_deps.json'
        
    def parse_requirements(self) -> Dict[str, Dict[str, str]]:
        """Parse requirements.txt and extract package versions"""
        packages = {}
        
        if not self.requirements_path.exists():
            return packages
        
        content = self.requirements_path.read_text()
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse package specifications
            # Formats: package==1.0.0, package>=1.0.0, package[extra]==1.0.0
            match = re.match(r'^([a-zA-Z0-9\-_\[\]]+)(==|>=|<=|>|<|~=)?([\d.]+)?', line)
            
            if match:
                package_name = match.group(1)
                operator = match.group(2) or '>='
                version = match.group(3) or 'latest'
                
                # Clean package name (remove extras like [cv])
                clean_name = re.sub(r'\[.*\]', '', package_name)
                
                packages[clean_name] = {
                    'name': package_name,  # Original name with extras
                    'clean_name': clean_name,
                    'operator': operator,
                    'current_version': version,
                    'line': line
                }
        
        return packages
    
    def get_latest_version(self, package_name: str) -> Optional[str]:
        """Fetch latest version from PyPI"""
        try:
            url = f'https://pypi.org/pypi/{package_name}/json'
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data['info']['version']
        except Exception as e:
            print(f"Error fetching version for {package_name}: {e}")
            return None
    
    def get_package_info(self, package_name: str) -> Optional[Dict]:
        """Get detailed package information from PyPI"""
        try:
            url = f'https://pypi.org/pypi/{package_name}/json'
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'name': data['info']['name'],
                'version': data['info']['version'],
                'summary': data['info']['summary'],
                'home_page': data['info'].get('home_page', ''),
                'author': data['info'].get('author', ''),
                'license': data['info'].get('license', ''),
                'requires_python': data['info'].get('requires_python', ''),
                'release_date': list(data['releases'].get(data['info']['version'], [{}]))[0].get('upload_time', '')
            }
        except Exception as e:
            print(f"Error fetching info for {package_name}: {e}")
            return None
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
        if v1 == 'latest' or v2 == 'latest':
            return -1 if v1 == 'latest' else 1
        
        try:
            # Handle versions with pre-release tags (e.g., 1.0.0rc1)
            v1_clean = re.match(r'^([\d.]+)', v1)
            v2_clean = re.match(r'^([\d.]+)', v2)
            
            if not v1_clean or not v2_clean:
                return 0
            
            parts1 = [int(x) for x in v1_clean.group(1).split('.')]
            parts2 = [int(x) for x in v2_clean.group(1).split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            
            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            
            return 0
        except Exception as e:
            print(f"Error comparing versions {v1} and {v2}: {e}")
            return 0
    
    def check_all_packages(self) -> Dict[str, Dict]:
        """Check all packages for updates"""
        packages = self.parse_requirements()
        results = {}
        
        for pkg_id, pkg_info in packages.items():
            latest = self.get_latest_version(pkg_info['clean_name'])
            current = pkg_info['current_version']
            
            if latest:
                # Determine if update is available
                update_available = False
                update_type = 'none'
                
                if current == 'latest' or pkg_info['operator'] == '>=':
                    # For >= operators, always show latest but don't flag as update needed
                    update_available = False
                    update_type = 'flexible'
                elif self.compare_versions(current, latest) < 0:
                    update_available = True
                    # Determine update type (major, minor, patch)
                    update_type = self._get_update_type(current, latest)
                
                results[pkg_id] = {
                    'name': pkg_info['name'],
                    'clean_name': pkg_info['clean_name'],
                    'current': current,
                    'latest': latest,
                    'operator': pkg_info['operator'],
                    'update_available': update_available,
                    'update_type': update_type,
                    'line': pkg_info['line']
                }
            else:
                results[pkg_id] = {
                    'name': pkg_info['name'],
                    'clean_name': pkg_info['clean_name'],
                    'current': current,
                    'latest': 'Unknown',
                    'operator': pkg_info['operator'],
                    'update_available': False,
                    'update_type': 'error',
                    'line': pkg_info['line']
                }
        
        return results
    
    def _get_update_type(self, current: str, latest: str) -> str:
        """Determine if update is major, minor, or patch"""
        try:
            current_parts = [int(x) for x in current.split('.')[:3]]
            latest_parts = [int(x) for x in latest.split('.')[:3]]
            
            # Pad to 3 parts
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(latest_parts) < 3:
                latest_parts.append(0)
            
            if current_parts[0] < latest_parts[0]:
                return 'major'
            elif current_parts[1] < latest_parts[1]:
                return 'minor'
            elif current_parts[2] < latest_parts[2]:
                return 'patch'
            else:
                return 'none'
        except:
            return 'unknown'
    
    def update_package(self, package_name: str, new_version: str, operator: str = '==') -> bool:
        """Update a specific package in requirements.txt"""
        if not self.requirements_path.exists():
            return False
        
        # Create backup
        backup_path = self.requirements_path.with_suffix('.txt.bak')
        self.requirements_path.rename(backup_path)
        
        try:
            content = backup_path.read_text()
            lines = content.split('\n')
            updated_lines = []
            
            for line in lines:
                # Check if this line contains the package
                if re.match(rf'^{re.escape(package_name)}(==|>=|<=|>|<|~=)', line):
                    # Update the version
                    updated_line = re.sub(
                        rf'^({re.escape(package_name)})(==|>=|<=|>|<|~=)([\d.]+)',
                        rf'\1{operator}{new_version}',
                        line
                    )
                    updated_lines.append(updated_line)
                else:
                    updated_lines.append(line)
            
            # Write updated content
            self.requirements_path.write_text('\n'.join(updated_lines))
            
            # Remove backup on success
            backup_path.unlink()
            return True
            
        except Exception as e:
            print(f"Error updating {package_name}: {e}")
            # Restore backup
            if backup_path.exists():
                backup_path.rename(self.requirements_path)
            return False
    
    def update_multiple_packages(self, updates: Dict[str, str]) -> Dict[str, bool]:
        """Update multiple packages at once"""
        results = {}
        
        for package_name, new_version in updates.items():
            # Get current operator
            packages = self.parse_requirements()
            operator = '=='
            
            for pkg_info in packages.values():
                if pkg_info['clean_name'] == package_name:
                    operator = pkg_info['operator']
                    break
            
            results[package_name] = self.update_package(package_name, new_version, operator)
        
        return results
    
    def save_check_results(self, results: Dict):
        """Save check results to config file"""
        self.config_path.parent.mkdir(exist_ok=True)
        
        data = {
            'last_check': datetime.now().isoformat(),
            'packages': results
        }
        
        self.config_path.write_text(json.dumps(data, indent=2))
    
    def load_check_results(self) -> Dict:
        """Load last check results"""
        if not self.config_path.exists():
            return {}
        
        try:
            return json.loads(self.config_path.read_text())
        except:
            return {}
    
    def get_security_advisories(self, package_name: str) -> List[Dict]:
        """Check for security advisories (placeholder - would need external API)"""
        # This would integrate with services like:
        # - PyUp Safety DB
        # - GitHub Security Advisories
        # - OSV (Open Source Vulnerabilities)
        # For now, return empty list
        return []


def main():
    """CLI interface for Python dependency checker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check and update Python dependencies')
    parser.add_argument('--check', action='store_true', help='Check for updates')
    parser.add_argument('--update', nargs='+', help='Update specific packages (e.g., Flask requests)')
    parser.add_argument('--update-all', action='store_true', help='Update all packages with available updates')
    parser.add_argument('--update-patch', action='store_true', help='Update only patch versions (safest)')
    parser.add_argument('--update-minor', action='store_true', help='Update patch and minor versions')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--info', help='Get detailed info about a package')
    
    args = parser.parse_args()
    
    checker = PythonDependencyChecker()
    
    if args.info:
        # Get package info
        info = checker.get_package_info(args.info)
        if info:
            print(f"\n📦 {info['name']} v{info['version']}\n")
            print(f"Summary: {info['summary']}")
            print(f"License: {info['license']}")
            print(f"Homepage: {info['home_page']}")
            print(f"Requires Python: {info['requires_python']}")
            print(f"Released: {info['release_date'][:10] if info['release_date'] else 'Unknown'}")
            print()
        else:
            print(f"❌ Could not fetch info for {args.info}")
    
    elif args.check or not any([args.update, args.update_all, args.update_patch, args.update_minor]):
        # Check for updates
        results = checker.check_all_packages()
        checker.save_check_results(results)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n📦 Python Dependency Version Check\n")
            print(f"{'Package':<30} {'Current':<15} {'Latest':<15} {'Type':<10} {'Status'}")
            print("-" * 90)
            
            for pkg_id, info in results.items():
                update_type = info.get('update_type', 'none')
                type_icon = {
                    'major': '🔴',
                    'minor': '🟡', 
                    'patch': '🟢',
                    'flexible': '📌',
                    'none': '✅',
                    'error': '❌'
                }.get(update_type, '❓')
                
                status = "⚠️  Update Available" if info['update_available'] else \
                        "📌 Flexible (>=)" if update_type == 'flexible' else \
                        "✅ Up to date"
                
                print(f"{info['clean_name']:<30} {info['current']:<15} {info['latest']:<15} {type_icon} {update_type:<8} {status}")
            
            print()
            
            # Summary
            total = len(results)
            updates_available = sum(1 for r in results.values() if r['update_available'])
            major_updates = sum(1 for r in results.values() if r.get('update_type') == 'major')
            minor_updates = sum(1 for r in results.values() if r.get('update_type') == 'minor')
            patch_updates = sum(1 for r in results.values() if r.get('update_type') == 'patch')
            
            print(f"📊 Summary: {total} packages total")
            print(f"   ⚠️  {updates_available} updates available")
            if major_updates:
                print(f"   🔴 {major_updates} major updates (breaking changes possible)")
            if minor_updates:
                print(f"   🟡 {minor_updates} minor updates (new features)")
            if patch_updates:
                print(f"   🟢 {patch_updates} patch updates (bug fixes)")
            print()
    
    elif args.update:
        # Update specific packages
        results = checker.check_all_packages()
        updates = {}
        
        for pkg_name in args.update:
            # Find package in results
            for pkg_id, info in results.items():
                if info['clean_name'].lower() == pkg_name.lower():
                    if info['latest'] != 'Unknown':
                        updates[info['clean_name']] = info['latest']
                    break
        
        if updates:
            print(f"\n🔄 Updating {len(updates)} packages...\n")
            update_results = checker.update_multiple_packages(updates)
            
            for pkg_name, success in update_results.items():
                status = "✅ Success" if success else "❌ Failed"
                print(f"{pkg_name}: {status}")
            print()
        else:
            print("\n❌ No matching packages found to update\n")
    
    elif args.update_all or args.update_patch or args.update_minor:
        # Update packages based on type
        results = checker.check_all_packages()
        updates = {}
        
        for pkg_id, info in results.items():
            if info['update_available']:
                update_type = info.get('update_type', 'none')
                
                should_update = False
                if args.update_all:
                    should_update = True
                elif args.update_patch and update_type == 'patch':
                    should_update = True
                elif args.update_minor and update_type in ['patch', 'minor']:
                    should_update = True
                
                if should_update and info['latest'] != 'Unknown':
                    updates[info['clean_name']] = info['latest']
        
        if updates:
            print(f"\n🔄 Updating {len(updates)} packages...\n")
            update_results = checker.update_multiple_packages(updates)
            
            for pkg_name, success in update_results.items():
                status = "✅ Success" if success else "❌ Failed"
                print(f"{pkg_name}: {status}")
            print()
        else:
            print("\n✅ All packages are up to date!\n")


if __name__ == '__main__':
    main()
