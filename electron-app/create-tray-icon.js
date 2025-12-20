// Quick script to create a simple tray icon
const fs = require('fs');
const { createCanvas } = require('canvas');

try {
  const canvas = createCanvas(32, 32);
  const ctx = canvas.getContext('2d');
  
  // Transparent background
  ctx.clearRect(0, 0, 32, 32);
  
  // Draw a simple circle with "O" inside
  ctx.fillStyle = '#000000';
  ctx.beginPath();
  ctx.arc(16, 16, 12, 0, Math.PI * 2);
  ctx.fill();
  
  ctx.fillStyle = '#FFFFFF';
  ctx.font = 'bold 18px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('O', 16, 16);
  
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync('tray-icon.png', buffer);
  console.log('✅ Created tray-icon.png');
} catch (err) {
  console.log('ℹ️ canvas module not installed, will use fallback icon');
}
