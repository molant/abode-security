# Claude Session Files

This directory contains guidance files for Claude Code sessions working on the `abode-security` integration.

## Files in This Directory

### `session-start.md`
**Read this first when starting a new session!**

Contains:
- Quick context check commands
- Project overview and location
- Current status summary
- Useful commands for common tasks
- File location guide

Use this to quickly understand where the project stands and what files matter.

### `phase-2-guide.md`
**Detailed implementation guide for Phase 2 tasks**

Contains:
- Overview of Phase 2 quality improvements
- Step-by-step tasks with code examples
- Testing procedures for each task
- Commit message templates
- Expected completion time estimates
- Success criteria

Use this when implementing Phase 2 features.

### `quick-ref.md`
**Quick lookup reference card**

Contains:
- Project info and key locations
- Status table
- Quick commands for common operations
- Architecture patterns and examples
- Common development tasks
- Phase progress visualization

Use this for quick lookups while working.

## How to Use These Files

### For New Sessions

1. Start with `session-start.md` - it tells you what to check first
2. Read `DEVELOPMENT.md` in project root for detailed status
3. Pick the phase guide for the phase you're working on
4. Use `quick-ref.md` while working for quick lookups

### For Quick Lookups

1. Use `quick-ref.md` for project structure or common commands
2. Use phase guides for detailed task information
3. Always check `DEVELOPMENT.md` for current status

### For New Tasks

1. Find the task in the relevant phase guide
2. Read the step-by-step instructions
3. Follow the "Testing Phase X Changes" section
4. Use the provided commit message templates
5. Update `DEVELOPMENT.md` when done

## Quick Start (Next Session)

```bash
# Navigate to project
cd /Users/molant/src/home-assistant-things/abode-security

# Read this session's guide
cat .claude/session-start.md

# Check project status
head -20 DEVELOPMENT.md

# See recent work
git log --oneline -5

# Start working on your task!
```

## File Relationships

```
.claude/README.md (you are here)
├── session-start.md (start here each session)
├── phase-2-guide.md (detailed Phase 2 implementation)
├── quick-ref.md (reference while working)
└── ../ (back to project root)
    ├── DEVELOPMENT.md (detailed project log)
    ├── DEVELOPMENT.md (current status and history)
    └── custom_components/abode_security/ (integration code)
```

## Key Takeaways

- **Always start with `session-start.md`**
- **Keep `DEVELOPMENT.md` updated** at the end of each session
- **Commit regularly** with clear messages
- **Use phase guides** for detailed task information
- **Use quick-ref.md** for lookups while working

## Session Structure

Each Claude Code session should follow this pattern:

### At Session Start
1. Read `.claude/session-start.md`
2. Check `DEVELOPMENT.md` for current status
3. Run `git log --oneline -10` to see recent work
4. Pick your task from the phase guide

### During Session
1. Work on your task following the phase guide
2. Refer to `quick-ref.md` for structure/commands
3. Test your changes
4. Commit frequently with clear messages

### At Session End
1. Update `DEVELOPMENT.md` with your progress
2. Make sure all work is committed
3. Note the next steps clearly
4. Push to remote if set up

---

**Last Updated:** 2025-11-23  
**Project Phase:** 1 (Setup) - Complete ✅  
**Next Phase:** 2 (Quality Improvements)
