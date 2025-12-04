# Deploy Analytics Features to Production

## Quick Deploy Commands

### Via SSH:
```bash
ssh wagesapp@192.168.1.202
cd ~/wages-app
git pull origin main
sudo supervisorctl restart wagesapp
```

### Or via Proxmox Console (as root):
```bash
cd /home/wagesapp/wages-app
su - wagesapp -c "cd /home/wagesapp/wages-app && git pull origin main"
supervisorctl restart wagesapp
```

## What's Being Deployed:

### New Features:
- ✅ Analytics tab with 4 visualizations
- ✅ Year-over-Year comparison charts
- ✅ Earnings forecast with predictions
- ✅ Client activity heatmap
- ✅ Weekly performance analysis

### Files Changed:
- `web_app.py` - 4 new API endpoints
- `templates/index.html` - New Analytics tab
- `static/js/analytics.js` - New visualization code

## Verification Steps:

1. Check app is running:
   ```bash
   sudo supervisorctl status wagesapp
   ```

2. View logs:
   ```bash
   tail -20 /var/log/wagesapp.out.log
   ```

3. Test in browser:
   - Visit: https://wages.daniel-hanson.co.uk
   - Click "Analytics" tab
   - Verify all 4 sections load

## Rollback (if needed):

```bash
cd /home/wagesapp/wages-app
git log --oneline -5
git checkout <previous-commit-hash>
sudo supervisorctl restart wagesapp
```

---

**Ready to deploy!** 🚀
