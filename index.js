/**
 * Example NPM plugin for Desktop MCP
 * Demonstrates mouse control and screenshot functionality
 */

const robot = require('robotjs');

class DesktopMCPPlugin {
    constructor() {
        this.initialized = false;
    }

    /**
     * Initialize the plugin
     */
    async initialize(config = {}) {
        try {
            // Set mouse delay if specified in config
            if (config.mouseDelay) {
                robot.setMouseDelay(config.mouseDelay);
            }
            
            this.initialized = true;
            return { success: true, message: "Plugin initialized successfully" };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Cleanup plugin resources
     */
    async cleanup() {
        this.initialized = false;
        return { success: true };
    }

    /**
     * Health check
     */
    async health_check() {
        return this.initialized;
    }

    /**
     * Get list of MCP functions this plugin provides
     */
    async get_mcp_functions() {
        return [
            'click_at',
            'double_click_at', 
            'right_click_at',
            'move_mouse_to',
            'get_mouse_position',
            'drag_and_drop',
            'scroll',
            'take_screenshot'
        ];
    }

    /**
     * Click at specific coordinates
     */
    async click_at({ x, y, button = 'left' }) {
        try {
            robot.moveMouse(x, y);
            robot.mouseClick(button);
            return { 
                success: true, 
                message: `${button} clicked at (${x}, ${y})` 
            };
        } catch (error) {
            throw new Error(`Failed to click at (${x}, ${y}): ${error.message}`);
        }
    }

    /**
     * Double click at specific coordinates
     */
    async double_click_at({ x, y, button = 'left' }) {
        try {
            robot.moveMouse(x, y);
            robot.mouseClick(button, true); // true for double click
            return { 
                success: true, 
                message: `Double ${button} clicked at (${x}, ${y})` 
            };
        } catch (error) {
            throw new Error(`Failed to double click at (${x}, ${y}): ${error.message}`);
        }
    }

    /**
     * Right click at specific coordinates
     */
    async right_click_at({ x, y }) {
        return await this.click_at({ x, y, button: 'right' });
    }

    /**
     * Move mouse to specific coordinates
     */
    async move_mouse_to({ x, y, smooth = false }) {
        try {
            if (smooth) {
                robot.moveMouseSmooth(x, y);
            } else {
                robot.moveMouse(x, y);
            }
            return { 
                success: true, 
                message: `Mouse moved to (${x}, ${y})` 
            };
        } catch (error) {
            throw new Error(`Failed to move mouse to (${x}, ${y}): ${error.message}`);
        }
    }

    /**
     * Get current mouse position
     */
    async get_mouse_position() {
        try {
            const pos = robot.getMousePos();
            return {
                x: pos.x,
                y: pos.y
            };
        } catch (error) {
            throw new Error(`Failed to get mouse position: ${error.message}`);
        }
    }

    /**
     * Drag and drop from start to end coordinates
     */
    async drag_and_drop({ start_x, start_y, end_x, end_y, button = 'left' }) {
        try {
            robot.moveMouse(start_x, start_y);
            robot.mouseToggle('down', button);
            robot.dragMouse(end_x, end_y);
            robot.mouseToggle('up', button);
            return { 
                success: true, 
                message: `Dragged from (${start_x}, ${start_y}) to (${end_x}, ${end_y})` 
            };
        } catch (error) {
            throw new Error(`Failed to drag and drop: ${error.message}`);
        }
    }

    /**
     * Scroll at current mouse position
     */
    async scroll({ direction = 'down', clicks = 3, x = null, y = null }) {
        try {
            if (x !== null && y !== null) {
                robot.moveMouse(x, y);
            }
            
            const scrollDirection = direction === 'up' ? 'up' : 'down';
            robot.scrollMouse(clicks, scrollDirection);
            
            return { 
                success: true, 
                message: `Scrolled ${direction} ${clicks} clicks` 
            };
        } catch (error) {
            throw new Error(`Failed to scroll: ${error.message}`);
        }
    }

    /**
     * Take a screenshot
     */
    async take_screenshot({ x = null, y = null, width = null, height = null } = {}) {
        try {
            let screenshot;
            
            if (x !== null && y !== null && width !== null && height !== null) {
                // Capture specific region
                screenshot = robot.screen.capture(x, y, width, height);
            } else {
                // Capture entire screen
                screenshot = robot.screen.capture();
            }
            
            // Convert to base64
            const image = screenshot.image;
            const png = robot.screen.captureFormat(image, 'png');
            const base64 = Buffer.from(png).toString('base64');
            
            return {
                image: base64,
                width: screenshot.width,
                height: screenshot.height,
                format: 'png'
            };
        } catch (error) {
            throw new Error(`Failed to take screenshot: ${error.message}`);
        }
    }
}

// Export the plugin instance
module.exports = new DesktopMCPPlugin();