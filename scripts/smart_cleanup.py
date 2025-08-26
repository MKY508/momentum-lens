#!/usr/bin/env python3
"""
Smart Code Cleanup Script for Momentum Lens
Analyzes and categorizes unused imports for intelligent cleanup
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json

# Categories of imports that might be useful even if unused
POTENTIALLY_USEFUL = {
    # UI feedback components - often needed for user interaction
    'CircularProgress': 'Loading states',
    'Alert': 'Error/success messages', 
    'Skeleton': 'Loading placeholders',
    'Snackbar': 'Notifications',
    'Dialog': 'Modal dialogs',
    'Backdrop': 'Loading overlays',
    
    # Form components - might be needed for future forms
    'TextField': 'Input fields',
    'FormControl': 'Form containers',
    'InputAdornment': 'Input decorations',
    'FormHelperText': 'Form help text',
    
    # Navigation and actions
    'IconButton': 'Icon actions',
    'Tooltip': 'Hover tips',
    'SpeedDial': 'Quick actions',
    'Fab': 'Floating action button',
    
    # Layout components
    'Stack': 'Layout stacking',
    'Paper': 'Card containers',
    'Container': 'Content containers',
    
    # Data display
    'LinearProgress': 'Progress bars',
    'Chip': 'Tags/labels',
    'Badge': 'Notification counts',
    
    # Icons - often needed
    'InfoIcon': 'Information display',
    'WarningIcon': 'Warnings',
    'ErrorIcon': 'Errors',
    'CheckCircleIcon': 'Success',
    'SpeedIcon': 'Performance',
    'CodeIcon': 'Code display',
    'FilterIcon': 'Filtering',
    'DashboardIcon': 'Dashboard',
    
    # React Query hooks - API management
    'useQuery': 'Data fetching',
    'useMutation': 'Data mutations',
    'useQueryClient': 'Cache management',
    
    # React hooks
    'useState': 'State management',
    'useEffect': 'Side effects',
    'useCallback': 'Callback optimization',
    'useMemo': 'Memoization',
    
    # Chart components - for data visualization
    'LineChart': 'Line charts',
    'BarChart': 'Bar charts',
    'Line': 'Chart lines',
    'Bar': 'Chart bars',
    'AreaChart': 'Area charts',
    'PieChart': 'Pie charts',
    
    # Type definitions - needed for TypeScript
    'Decision': 'Decision type',
    'MarketIndicator': 'Market data type',
    'TradeLog': 'Trade log type',
    'AlertType': 'Alert type',
    'PerformanceMetrics': 'Performance type',
    'Holding': 'Holdings type',
    'DCASchedule': 'DCA schedule type',
    'MomentumETF': 'ETF type',
    'CorrelationMatrix': 'Correlation type',
    
    # Utility functions
    'debounce': 'Input debouncing',
    'throttle': 'Event throttling',
    'addDays': 'Date manipulation',
    'format': 'Date formatting',
}

# Definitely safe to remove - truly unused
SAFE_TO_REMOVE = {
    'Link': 'Not using routing links',
    'Button': 'Using IconButton instead',
    'ListItemSecondaryAction': 'Not using secondary actions',
}

class SmartCleanup:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.frontend_src = self.project_root / 'frontend' / 'src'
        self.backend_root = self.project_root / 'backend'
        self.cleanup_report = {
            'analyzed_files': 0,
            'total_unused': 0,
            'removed': [],
            'kept': [],
            'potentially_useful': []
        }
    
    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single file for unused imports"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract imports (simplified - real implementation would use AST)
        import_pattern = r'import\s+(?:{([^}]+)}|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]'
        imports = re.findall(import_pattern, content)
        
        unused = []
        for match in imports:
            if match[0]:  # Named imports
                for name in match[0].split(','):
                    name = name.strip()
                    # Check if used in file (simplified check)
                    if content.count(name) <= 1:  # Only in import
                        unused.append(name)
        
        return {
            'file': str(file_path.relative_to(self.project_root)),
            'unused': unused
        }
    
    def categorize_imports(self, unused_imports: List[str]) -> Tuple[List[str], List[str]]:
        """Categorize imports into safe to remove vs potentially useful"""
        safe_to_remove = []
        potentially_useful = []
        
        for import_name in unused_imports:
            if import_name in SAFE_TO_REMOVE:
                safe_to_remove.append(import_name)
            elif import_name in POTENTIALLY_USEFUL:
                potentially_useful.append(import_name)
            else:
                # Default: if we don't know, consider it safe to remove
                safe_to_remove.append(import_name)
        
        return safe_to_remove, potentially_useful
    
    def generate_cleanup_plan(self) -> str:
        """Generate a detailed cleanup plan"""
        report = []
        report.append("# Momentum Lens Smart Cleanup Plan\n")
        report.append("## Analysis Summary\n")
        report.append(f"- Files analyzed: {self.cleanup_report['analyzed_files']}")
        report.append(f"- Total unused imports: {self.cleanup_report['total_unused']}")
        report.append(f"- Safe to remove: {len(self.cleanup_report['removed'])}")
        report.append(f"- Potentially useful (kept): {len(self.cleanup_report['potentially_useful'])}\n")
        
        report.append("## Imports to Remove (Definitely Unused)\n")
        for item in self.cleanup_report['removed']:
            report.append(f"- **{item['import']}** in `{item['file']}`: {item['reason']}")
        
        report.append("\n## Imports to Keep (Potentially Useful)\n")
        for item in self.cleanup_report['potentially_useful']:
            report.append(f"- **{item['import']}** in `{item['file']}`: {item['reason']}")
        
        report.append("\n## Port Configuration Fix\n")
        report.append("Standardizing all ports:")
        report.append("- Frontend: 3000")
        report.append("- Backend API: 8000")
        report.append("- WebSocket: ws://localhost:8000")
        
        return '\n'.join(report)
    
    def fix_ports(self):
        """Ensure consistent port configuration"""
        fixes = []
        
        # Fix docker-compose.monitoring.yml - Grafana should use 3001
        monitoring_file = self.project_root / 'docker-compose.monitoring.yml'
        if monitoring_file.exists():
            with open(monitoring_file, 'r') as f:
                content = f.read()
            # Grafana uses port 3001 to avoid conflict with frontend
            if '${GRAFANA_PORT:-3001}:3000' in content:
                fixes.append("✓ Grafana correctly configured on port 3001")
        
        # Check .env file
        env_file = self.project_root / '.env'
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
            if 'FRONTEND_URL=http://localhost:3000' in content and \
               'BACKEND_URL=http://localhost:8000' in content:
                fixes.append("✓ Environment variables correctly configured")
        
        return fixes

def main():
    project_root = '/Users/maokaiyue/momentum-lens'
    cleaner = SmartCleanup(project_root)
    
    # Example analysis for App.tsx based on ESLint warnings
    example_unused = {
        'App.tsx': ['CircularProgress', 'Alert', 'dataSourceManager'],
        'DataSourceStatus.tsx': ['SpeedIcon'],
        'CoreModule.tsx': ['useState', 'addDays', 'Holding', 'DCASchedule'],
        'DecisionDashboard.tsx': ['useEffect', 'InfoIcon', 'Decision', 'MarketIndicator'],
        'LogsKPI.tsx': ['FilterIcon', 'LineChart', 'Line', 'BarChart', 'Bar', 'TradeLog', 'AlertType', 'PerformanceMetrics'],
        'APIConfiguration.tsx': ['Stack', 'LinearProgress', 'ListItemSecondaryAction', 'Paper', 'useQuery', 'useMutation'],
    }
    
    # Analyze each file
    for file_name, unused_imports in example_unused.items():
        cleaner.cleanup_report['analyzed_files'] += 1
        cleaner.cleanup_report['total_unused'] += len(unused_imports)
        
        safe_to_remove, potentially_useful = cleaner.categorize_imports(unused_imports)
        
        for import_name in safe_to_remove:
            cleaner.cleanup_report['removed'].append({
                'file': file_name,
                'import': import_name,
                'reason': SAFE_TO_REMOVE.get(import_name, 'Not used in component')
            })
        
        for import_name in potentially_useful:
            cleaner.cleanup_report['potentially_useful'].append({
                'file': file_name,
                'import': import_name,
                'reason': POTENTIALLY_USEFUL.get(import_name, 'May be needed')
            })
    
    # Generate and save report
    report = cleaner.generate_cleanup_plan()
    report_path = Path(project_root) / 'SMART_CLEANUP_PLAN.md'
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"✅ Smart cleanup plan generated: {report_path}")
    print(f"📊 Summary:")
    print(f"   - Total unused: {cleaner.cleanup_report['total_unused']}")
    print(f"   - Safe to remove: {len(cleaner.cleanup_report['removed'])}")
    print(f"   - Keep (potentially useful): {len(cleaner.cleanup_report['potentially_useful'])}")
    
    # Fix ports
    port_fixes = cleaner.fix_ports()
    for fix in port_fixes:
        print(f"   {fix}")

if __name__ == '__main__':
    main()