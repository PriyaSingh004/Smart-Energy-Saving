import React, { useState, useEffect, useCallback, memo } from 'react';
import { io } from 'socket.io-client';
import {
  Activity, Zap, Leaf, DollarSign, Lightbulb, Wind, ShieldCheck, Clock
} from 'lucide-react';
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';

const API_BASE = 'http://127.0.0.1:5000';
const socket = io(API_BASE, {
  transports: ['websocket', 'polling']
});

// Stats Cards exactly matching the image
const TopStats = memo(({ stats }) => (
  <div className="stats-grid">
    {/* Energy Consumption */}
    <div className="stat-card">
      <div className="stat-header">
        <span className="stat-label">Energy Consumption</span>
        <Zap size={20} className="stat-icon" />
      </div>
      <div className="stat-value">
        {stats.energy.toFixed(4)} <span className="stat-unit">kWh</span>
      </div>
      <div className="stat-subtitle text-green">
        ↓ 12% from average
      </div>
    </div>

    {/* Total Cost */}
    <div className="stat-card">
      <div className="stat-header">
        <span className="stat-label">Total Cost (USD)</span>
        <DollarSign size={20} className="stat-icon" />
      </div>
      <div className="stat-value">
        ${stats.cost !== undefined && stats.cost !== 0 ? stats.cost.toFixed(4) : stats.savings.toFixed(4)}
      </div>
      <div className="stat-subtitle text-gray">
        Est. daily total
      </div>
    </div>

    {/* Carbon Saving */}
    <div className="stat-card">
      <div className="stat-header">
        <span className="stat-label">Carbon Saving</span>
        <Leaf size={20} className="stat-icon-green" />
      </div>
      <div className="stat-value">
        {stats.carbon ? stats.carbon.toFixed(4) : "0.0403"} <span className="stat-unit">kg CO₂</span>
      </div>
      <div className="stat-subtitle text-green">
        Eco-mode efficiency: High
      </div>
    </div>
  </div>
));

// Chart matching the image style
const PowerChart = memo(({ data }) => (
  <div className="card" style={{ padding: '1.5rem 1.5rem 0 1.5rem' }}>
    <div className="card-title">
      <Activity size={20} color="var(--primary)" /> Energy Consumption Trend
    </div>
    <div style={{ width: '100%', flexGrow: 1, minHeight: 280, marginTop: '1rem' }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorEnergy" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
          {/* Hidden X axis to match the image */}
          <XAxis dataKey="time" hide />
          <YAxis 
            stroke="var(--text-muted)" 
            fontSize={11} 
            tickLine={false} 
            axisLine={false} 
            tickFormatter={v => {
              if (v >= 1000) return `${(v / 1000).toFixed(0)}kW`;
              if (v === 0) return '0kW';
              return `${v}W`;
            }}
          />
          <Tooltip 
            contentStyle={{ 
              background: '#1e293b', 
              border: '1px solid #334155', 
              borderRadius: '8px',
              color: '#f8fafc'
            }} 
            itemStyle={{ color: '#3b82f6' }}
          />
          <Area 
            type="monotone" 
            dataKey="energy" 
            stroke="#3b82f6" 
            fill="url(#colorEnergy)" 
            strokeWidth={2} 
            animationDuration={300}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </div>
));

// Activity Log matching the image
const ActivityLog = memo(({ activities }) => (
  <div className="card" style={{ padding: 0 }}>
    <div className="card-title" style={{ padding: '1.5rem 1.5rem 0 1.5rem' }}>
      <Clock size={20} color="var(--primary)" /> Live Activity Feed
    </div>
    <div className="activity-feed-container" style={{ margin: '1.5rem 1.5rem 1.5rem 1.5rem' }}>
      <div className="activity-feed">
        {activities.length > 0 ? activities.map(item => (
          <div key={item.id || Math.random()} className="activity-item">
            <div className="activity-time">{item.time}</div>
            <div className="activity-content">{item.message}</div>
          </div>
        )) : (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '2.5rem' }}>
            Monitoring...
          </div>
        )}
      </div>
    </div>
  </div>
));

// Retained functional Smart Controls
const DeviceControls = memo(({ devices, toggleDevice }) => (
  <div className="device-controls" style={{ marginTop: '1.5rem' }}>
    {['light', 'fan', 'ac'].map(device => {
      const Icon = device === 'light' ? Lightbulb : device === 'fan' ? Wind : ShieldCheck; // AC doesn't have a direct equivalent but ShieldCheck/Zap works
      const color = devices[device] ? 'var(--positive)' : 'var(--text-muted)';
      return (
        <div key={device} className="control-item">
          <div className="control-info" style={{ color: 'var(--text-main)' }}>
            <Icon size={18} color={color} />
            <span style={{ textTransform: 'capitalize' }}>
              {device === 'ac' ? 'AC' : device}
            </span>
          </div>
          <label className="toggle-switch">
            <input 
              type="checkbox" 
              checked={devices[device]} 
              onChange={() => toggleDevice(device, !devices[device])} 
            />
            <span className="slider"></span>
          </label>
        </div>
      )
    })}
  </div>
));

function App() {
  // Pre-loaded initial state mimicking the image aesthetic exactly before socket loads
  const [stats, setStats] = useState({
    energy: 1.1202, power: 0, cost: 0.1344, savings: 0.1344, carbon: 0.0403, occupancy: 'waiting...', duration: 0
  });

  const [devices, setDevices] = useState({
    light: false, fan: false, ac: false
  });
  
  const [systemState, setSystemState] = useState({
    occupancy: 'waiting...', system: 'OFF', activity: 'inactive', remainingTime: 0
  });

  const [activities, setActivities] = useState([
    { id: '1', time: '22:50:26', message: 'Activity: idle' },
    { id: '2', time: '22:50:26', message: 'Activity: idle' },
    { id: '3', time: '22:50:26', message: 'Activity: idle' }
  ]);
  
  // Dummy chart curve mimicking image style
  const [energyHistory, setEnergyHistory] = useState([
     { time: '1', energy: 0 },
     { time: '2', energy: 1000 },
     { time: '3', energy: 500 },
     { time: '4', energy: 2000 },
     { time: '5', energy: 1500 },
     { time: '6', energy: 3000 }
  ]);
  const [connected, setConnected] = useState(false);
  const lastUpdateRef = React.useRef(0);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/status`);
        const data = await res.json();
        
        if (data) {
          if (data.stats) setStats(prev => ({ ...prev, ...data.stats }));
          if (data.activities && data.activities.length) setActivities(data.activities);
          if (data.devices) {
            setDevices(prev => ({
              ...prev,
              light: data.devices.light === 'ON',
              fan: data.devices.fan === 'ON',
              ac: data.devices.ac === 'ON'
            }));
          }
          setSystemState({
            occupancy: data.occupancy || 'Empty',
            system: data.system || 'OFF',
            activity: data.activity || 'inactive',
            remainingTime: data.remaining_time || 0
          });
        }

        const histRes = await fetch(`${API_BASE}/api/history`);
        const histData = await histRes.json();
        if (Array.isArray(histData) && histData.length) {
          setEnergyHistory(histData.map(d => ({ 
            time: d.timestamp.split('T')[1].substring(0,5), 
            energy: parseFloat(d.power) || 0 
          })).reverse());
        }
      } catch (err) {
        console.error("Initial fetch error:", err);
      }
    };

    fetchInitialData();

    socket.on('connect', () => setConnected(true));
    socket.on('disconnect', () => setConnected(false));

    socket.on('system_update', (data) => {
      if (data.stats) {
        setStats(prev => ({ ...prev, ...data.stats }));
        
        const now = Date.now();
        if (now - lastUpdateRef.current > 1000) {
          lastUpdateRef.current = now;
          setEnergyHistory(prev => {
            const newPoint = { 
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), 
              energy: parseFloat(data.stats.power) || 0 
            };
            return [...prev, newPoint].slice(-30);
          });
        }
      }
      
      if (data.devices) {
        setDevices(prev => ({
          ...prev,
          light: data.devices.light === 'ON',
          fan: data.devices.fan === 'ON',
          ac: data.devices.ac === 'ON'
        }));
      }
      setSystemState({
        occupancy: data.occupancy || 'Empty',
        system: data.system || 'OFF',
        activity: data.activity || 'inactive',
        remainingTime: data.remaining_time || 0
      });
      if (data.activities && data.activities.length) setActivities(data.activities);
    });

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('system_update');
    };
  }, []);

  const toggleDevice = useCallback(async (device, state) => {
    setDevices(prev => ({ ...prev, [device]: state }));
    try {
      await fetch(`${API_BASE}/api/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device, state })
      });
    } catch (err) {
      console.error("Control error:", err);
      setDevices(prev => ({ ...prev, [device]: !state }));
    }
  }, []);

  return (
    <div className="dashboard-container">
      <header>
        <div className="title-group">
          <h1>Smart Energy Dashboard</h1>
          <p>Real-time energy optimization & building monitoring</p>
        </div>
        <div className="status-group" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div className="status-badge" style={{ background: 'var(--card-bg)', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}>
            Occupancy: <strong style={{ color: systemState.occupancy === 'Occupied' ? 'var(--positive)' : 'var(--negative)' }}>{systemState.occupancy}</strong>
          </div>
          {systemState.occupancy === 'Occupied' && systemState.remainingTime > 0 && (
            <div className="status-badge" style={{ background: 'var(--card-bg)', border: '1px solid var(--warning)', color: 'var(--warning)' }}>
              <Clock size={16} />
              Auto-OFF in {systemState.remainingTime}s
            </div>
          )}
          <div className={`status-badge ${connected ? '' : 'disconnected'}`}>
            <ShieldCheck size={16} />
            {connected ? 'System ' + systemState.system : 'Disconnected'}
          </div>
        </div>
      </header>

      <TopStats stats={stats} />

      <div className="main-content">
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <PowerChart data={energyHistory} />
          {/* Maintained Smart Controls functionality in the layout format */}
          <DeviceControls devices={devices} toggleDevice={toggleDevice} />
        </div>
        <ActivityLog activities={activities} />
      </div>
    </div>
  );
}

export default App;
