import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../services/creditsAPI';
import './NotificationBell.css';

const POLL_INTERVAL_MS = 30000;

function NotificationBell() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await getNotifications();
      if (data.success) {
        setNotifications(data.notifications);
        setUnreadCount(data.unread_count);
      }
    } catch (err) {
      // Silent — a failed poll shouldn't disrupt the UI. It'll retry on the next interval.
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const id = setInterval(fetchNotifications, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchNotifications]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggle = () => setOpen((o) => !o);

  const handleNotificationClick = async (notif) => {
    if (!notif.is_read) {
      setNotifications((prev) => prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n)));
      setUnreadCount((c) => Math.max(c - 1, 0));
      try {
        await markNotificationRead(notif.id);
      } catch (err) {
        // Best-effort — UI already updated optimistically.
      }
    }
  };

  const handleMarkAllRead = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
    try {
      await markAllNotificationsRead();
    } catch (err) {
      // Best-effort.
    }
  };

  return (
    <div className="notif-bell-wrapper" ref={wrapperRef}>
      <button className="notif-bell-btn" onClick={handleToggle} type="button" aria-label="Notifications">
        🔔
        {unreadCount > 0 && <span className="notif-bell-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>}
      </button>

      {open && (
        <div className="notif-dropdown">
          <div className="notif-dropdown-header">
            <span>Notifications</span>
            {unreadCount > 0 && (
              <button className="notif-mark-all" onClick={handleMarkAllRead} type="button">
                Mark all read
              </button>
            )}
          </div>
          <div className="notif-list">
            {notifications.length === 0 && (
              <div className="notif-empty">Nothing yet — we'll let you know.</div>
            )}
            {notifications.map((n) => (
              <button
                key={n.id}
                className={`notif-item${n.is_read ? '' : ' notif-item--unread'}`}
                onClick={() => handleNotificationClick(n)}
                type="button"
              >
                <span className="notif-item-title">{n.title}</span>
                <span className="notif-item-body">{n.body}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationBell;
