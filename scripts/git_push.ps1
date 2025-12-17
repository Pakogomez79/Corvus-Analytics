$s = git status --porcelain
if ($s -and $s.Trim() -ne "") {
    try {
        git rev-parse --verify 'feature/breadcrumbs-config-20251217' > $null 2>&1
        $exists = $true
    } catch {
        $exists = $false
    }
    if ($exists) {
        git checkout 'feature/breadcrumbs-config-20251217'
    } else {
        git checkout -b 'feature/breadcrumbs-config-20251217'
    }
    git add -A
    git commit -m 'feat(ui): normalizar breadcrumbs, mover XBRL y añadir pantallas de configuración' -q
    git push -u origin 'feature/breadcrumbs-config-20251217'
} else {
    Write-Host 'No hay cambios para commitear.'
}
