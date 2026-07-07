// frontend_web/src/components/Dashboard/AnatomicalMap.jsx
import React, { useState, useRef, useEffect } from 'react';
import './AnatomicalMap.css';

// ============================================
// AUSCULTATION POINTS
// ============================================
const AUSCULTATION_POINTS = {
  MV: {
    id: 'MV',
    label: 'Mitral Valve',
    shortLabel: 'MV',
    description: 'Apex / 5th intercostal space',
    icon: '🫀',
    color: '#3b82f6',
    bgColor: 'rgba(59, 130, 246, 0.15)',
    x: 48,
    y: 58,
    size: 32
  },
  AV: {
    id: 'AV',
    label: 'Aortic Valve',
    shortLabel: 'AV',
    description: 'Right upper sternal border',
    icon: '❤️',
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.15)',
    x: 62,
    y: 38,
    size: 28
  },
  PV: {
    id: 'PV',
    label: 'Pulmonary Valve',
    shortLabel: 'PV',
    description: 'Left upper sternal border',
    icon: '💙',
    color: '#8b5cf6',
    bgColor: 'rgba(139, 92, 246, 0.15)',
    x: 38,
    y: 38,
    size: 28
  },
  TV: {
    id: 'TV',
    label: 'Tricuspid Valve',
    shortLabel: 'TV',
    description: 'Left lower sternal border',
    icon: '💚',
    color: '#22c55e',
    bgColor: 'rgba(34, 197, 94, 0.15)',
    x: 48,
    y: 75,
    size: 30
  }
};

// ============================================
// MAIN COMPONENT
// ============================================
const AnatomicalMap = ({ 
  selectedPoint = 'MV',
  onPointSelect,
  onClose,
  isOpen = false,
  showLabels = true,
  interactive = true,
  size = 'medium'
}) => {
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const svgRef = useRef(null);

  // Size configurations
  const sizes = {
    small: { width: 180, height: 200, fontSize: 10, labelSize: 8 },
    medium: { width: 280, height: 310, fontSize: 12, labelSize: 10 },
    large: { width: 400, height: 440, fontSize: 14, labelSize: 12 }
  };

  const config = sizes[size] || sizes.medium;

  // Handle point selection
  const handlePointClick = (pointId) => {
    if (!interactive) return;
    if (onPointSelect) {
      onPointSelect(pointId);
    }
  };

  // Handle hover
  const handlePointHover = (pointId, event) => {
    if (!interactive) return;
    setHoveredPoint(pointId);
    
    if (pointId && event) {
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) {
        setTooltipPosition({
          x: event.clientX - rect.left + 12,
          y: event.clientY - rect.top - 10
        });
      }
    }
  };

  // Draw heart shape SVG path
  const heartPath = `
    M 50 30
    C 50 30, 20 10, 20 35
    C 20 55, 50 80, 50 85
    C 50 80, 80 55, 80 35
    C 80 10, 50 30, 50 30
    Z
  `;

  // Scale coordinates to SVG viewBox
  const scaleX = (x) => (x / 100) * 100;
  const scaleY = (y) => (y / 100) * 100;

  // Get point SVG position
  const getPointPosition = (point) => ({
    cx: scaleX(point.x),
    cy: scaleY(point.y),
    r: point.size / 2
  });

  // Render auscultation point
  const renderPoint = (pointId) => {
    const point = AUSCULTATION_POINTS[pointId];
    if (!point) return null;

    const isSelected = selectedPoint === pointId;
    const isHovered = hoveredPoint === pointId;
    const pos = getPointPosition(point);

    return (
      <g
        key={pointId}
        className={`anatomical-point ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
        onClick={() => handlePointClick(pointId)}
        onMouseEnter={(e) => handlePointHover(pointId, e)}
        onMouseLeave={() => handlePointHover(null)}
        style={{ cursor: interactive ? 'pointer' : 'default' }}
      >
        {/* Point background glow */}
        {(isSelected || isHovered) && (
          <circle
            cx={pos.cx}
            cy={pos.cy}
            r={pos.r + 12}
            fill={point.bgColor}
            opacity={0.3}
            className="point-glow"
          />
        )}

        {/* Main point circle */}
        <circle
          cx={pos.cx}
          cy={pos.cy}
          r={pos.r}
          fill={isSelected ? point.color : 'white'}
          stroke={point.color}
          strokeWidth={isSelected ? 3 : 2}
          className="point-circle"
        />

        {/* Point label inside circle */}
        {showLabels && (
          <text
            x={pos.cx}
            y={pos.cy + 4}
            textAnchor="middle"
            fontSize={config.labelSize}
            fontWeight={isSelected ? '700' : '500'}
            fill={isSelected ? 'white' : point.color}
            className="point-label"
          >
            {point.shortLabel}
          </text>
        )}

        {/* Pulsing animation ring for selected point */}
        {isSelected && (
          <circle
            cx={pos.cx}
            cy={pos.cy}
            r={pos.r + 6}
            fill="none"
            stroke={point.color}
            strokeWidth={2}
            opacity={0.4}
            className="pulse-ring"
          >
            <animate
              attributeName="r"
              from={pos.r + 4}
              to={pos.r + 16}
              dur="1.5s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              from="0.6"
              to="0"
              dur="1.5s"
              repeatCount="indefinite"
            />
          </circle>
        )}

        {/* Point label outside */}
        {showLabels && (
          <text
            x={pos.cx}
            y={pos.cy - pos.r - 8}
            textAnchor="middle"
            fontSize={config.fontSize}
            fill="#1a1a2e"
            fontWeight={isSelected ? '600' : '400'}
            className="point-name"
          >
            {point.shortLabel}
          </text>
        )}
      </g>
    );
  };

  // Render tooltip
  const renderTooltip = () => {
    if (!hoveredPoint || !interactive) return null;
    const point = AUSCULTATION_POINTS[hoveredPoint];
    if (!point) return null;

    return (
      <div
        className="anatomical-tooltip"
        style={{
          left: tooltipPosition.x,
          top: tooltipPosition.y,
          position: 'absolute',
          pointerEvents: 'none'
        }}
      >
        <div className="tooltip-content">
          <div className="tooltip-header">
            <span className="tooltip-icon">{point.icon}</span>
            <span className="tooltip-title">{point.label}</span>
          </div>
          <div className="tooltip-description">{point.description}</div>
          <div className="tooltip-status">
            {selectedPoint === hoveredPoint ? '✅ Selected' : 'Click to select'}
          </div>
        </div>
      </div>
    );
  };

  // Render legend
  const renderLegend = () => {
    if (!showLabels) return null;

    return (
      <div className="anatomical-legend">
        <div className="legend-title">Auscultation Points</div>
        <div className="legend-items">
          {Object.values(AUSCULTATION_POINTS).map((point) => (
            <div
              key={point.id}
              className={`legend-item ${selectedPoint === point.id ? 'active' : ''}`}
              onClick={() => handlePointClick(point.id)}
              style={{ cursor: interactive ? 'pointer' : 'default' }}
            >
              <span
                className="legend-dot"
                style={{ backgroundColor: point.color }}
              />
              <span className="legend-label">{point.shortLabel}</span>
              <span className="legend-name">{point.label}</span>
              {selectedPoint === point.id && (
                <span className="legend-check">✓</span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  // If not open, return null
  if (!isOpen) {
    return null;
  }

  return (
    <div className="anatomical-map-container" ref={containerRef}>
      <div className="anatomical-map-wrapper">
        {/* Close button */}
        {onClose && (
          <button className="map-close-btn" onClick={onClose}>
            ×
          </button>
        )}

        <div className="map-header">
          <h3>Interactive Heart Map</h3>
          <p className="map-subtitle">Select auscultation point</p>
        </div>

        <div className="map-body">
          {/* SVG Heart Map */}
          <div className="map-svg-container" style={{ width: config.width + 60, height: config.height + 40 }}>
            <svg
              ref={svgRef}
              viewBox="0 0 100 100"
              style={{ width: '100%', height: '100%' }}
              className="heart-svg"
            >
              {/* Heart background */}
              <defs>
                <radialGradient id="heartGradient" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#fee2e2" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#fee2e2" stopOpacity="0" />
                </radialGradient>
                <filter id="heartShadow">
                  <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.1" />
                </filter>
              </defs>

              {/* Heart shape background */}
              <path
                d={heartPath}
                fill="url(#heartGradient)"
                stroke="#e2e8f0"
                strokeWidth="1"
                filter="url(#heartShadow)"
                className="heart-shape"
              />

              {/* Heart outline */}
              <path
                d={heartPath}
                fill="none"
                stroke="#94a3b8"
                strokeWidth="0.5"
                opacity="0.3"
              />

              {/* Aorta outline */}
              <path
                d="M 50 35 C 55 25, 65 20, 70 25 C 75 30, 72 40, 68 42"
                fill="none"
                stroke="#94a3b8"
                strokeWidth="0.5"
                opacity="0.3"
              />

              {/* Pulmonary artery outline */}
              <path
                d="M 50 35 C 45 25, 35 20, 30 25 C 25 30, 28 40, 32 42"
                fill="none"
                stroke="#94a3b8"
                strokeWidth="0.5"
                opacity="0.3"
              />

              {/* Auscultation points */}
              {Object.keys(AUSCULTATION_POINTS).map(renderPoint)}

              {/* Tooltip */}
              {renderTooltip()}
            </svg>
          </div>

          {/* Legend */}
          {renderLegend()}
        </div>

        {/* Instructions */}
        {interactive && (
          <div className="map-footer">
            <p className="map-instructions">
              💡 Click on any point to select the auscultation area
            </p>
            <p className="map-selected">
              Selected: <strong style={{ color: AUSCULTATION_POINTS[selectedPoint]?.color }}>
                {AUSCULTATION_POINTS[selectedPoint]?.label || 'None'}
              </strong>
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// TRIGGER COMPONENT
// ============================================

export const AnatomicalMapTrigger = ({ 
  selectedPoint = 'MV',
  onClick,
  compact = false
}) => {
  const point = AUSCULTATION_POINTS[selectedPoint];
  
  if (!point) return null;

  return (
    <button 
      className="anatomical-map-trigger"
      onClick={onClick}
      title="Open anatomical map"
    >
      <div className="trigger-content">
        <div 
          className="trigger-dot"
          style={{ backgroundColor: point.color }}
        />
        <span className="trigger-label">
          {compact ? point.shortLabel : point.label}
        </span>
        <svg 
          width="16" 
          height="16" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2"
          className="trigger-icon"
        >
          <path d="M2 12 L6 8 L6 16 L2 12 Z" />
          <path d="M22 12 L18 8 L18 16 L22 12 Z" />
          <path d="M6 12 L18 12" />
          <path d="M12 6 L12 18" />
        </svg>
      </div>
    </button>
  );
};

export default AnatomicalMap;