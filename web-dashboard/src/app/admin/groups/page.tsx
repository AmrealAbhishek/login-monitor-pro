'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import {
  Users,
  Plus,
  Trash2,
  Edit2,
  Save,
  X,
  Monitor,
  Palette,
  UserCheck,
  FolderOpen,
  ChevronRight,
} from 'lucide-react';

interface DeviceGroup {
  id: string;
  name: string;
  description: string | null;
  color: string;
  icon: string;
  created_at: string;
  device_count?: number;
}

interface Device {
  id: string;
  device_name: string | null;
  hostname: string;
  os: string;
  last_seen: string;
  group_ids?: string[];
}

const colorOptions = [
  { value: '#EF4444', label: 'Red' },
  { value: '#F97316', label: 'Orange' },
  { value: '#EAB308', label: 'Yellow' },
  { value: '#22C55E', label: 'Green' },
  { value: '#3B82F6', label: 'Blue' },
  { value: '#8B5CF6', label: 'Purple' },
  { value: '#EC4899', label: 'Pink' },
  { value: '#6B7280', label: 'Gray' },
];

export default function DeviceGroupsPage() {
  const [groups, setGroups] = useState<DeviceGroup[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<DeviceGroup | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<DeviceGroup | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    color: '#3B82F6',
  });

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    // Fetch groups
    const { data: groupsData, error: groupsError } = await supabase
      .from('device_groups')
      .select('*')
      .order('name');

    if (groupsData) {
      // Get device counts for each group
      const groupsWithCounts = await Promise.all(
        groupsData.map(async (group) => {
          const { count } = await supabase
            .from('device_group_members')
            .select('*', { count: 'exact', head: true })
            .eq('group_id', group.id);
          return { ...group, device_count: count || 0 };
        })
      );
      setGroups(groupsWithCounts);
    }
    if (groupsError) console.error('Error fetching groups:', groupsError);

    // Fetch devices with their group memberships
    const { data: devicesData } = await supabase
      .from('devices')
      .select('id, device_name, hostname, os, last_seen')
      .order('hostname');

    if (devicesData) {
      // Get group memberships for each device
      const devicesWithGroups = await Promise.all(
        devicesData.map(async (device) => {
          const { data: memberships } = await supabase
            .from('device_group_members')
            .select('group_id')
            .eq('device_id', device.id);
          return {
            ...device,
            group_ids: memberships?.map(m => m.group_id) || [],
          };
        })
      );
      setDevices(devicesWithGroups);
    }

    setLoading(false);
  }

  async function saveGroup() {
    if (!formData.name) return;

    const groupData = {
      name: formData.name,
      description: formData.description || null,
      color: formData.color,
    };

    if (editingGroup) {
      const { error } = await supabase
        .from('device_groups')
        .update(groupData)
        .eq('id', editingGroup.id);

      if (error) {
        console.error('Error updating group:', error);
        return;
      }
    } else {
      const { error } = await supabase
        .from('device_groups')
        .insert(groupData);

      if (error) {
        console.error('Error creating group:', error);
        return;
      }
    }

    setShowModal(false);
    setEditingGroup(null);
    resetForm();
    fetchData();
  }

  async function deleteGroup(id: string) {
    if (!confirm('Are you sure you want to delete this group? Devices will be removed from the group.')) return;

    const { error } = await supabase
      .from('device_groups')
      .delete()
      .eq('id', id);

    if (!error) {
      if (selectedGroup?.id === id) setSelectedGroup(null);
      fetchData();
    }
  }

  async function toggleDeviceInGroup(deviceId: string, groupId: string, isMember: boolean) {
    if (isMember) {
      // Remove from group
      const { error } = await supabase
        .from('device_group_members')
        .delete()
        .eq('device_id', deviceId)
        .eq('group_id', groupId);

      if (!error) {
        setDevices(devices.map(d =>
          d.id === deviceId
            ? { ...d, group_ids: d.group_ids?.filter(g => g !== groupId) }
            : d
        ));
        setGroups(groups.map(g =>
          g.id === groupId
            ? { ...g, device_count: (g.device_count || 1) - 1 }
            : g
        ));
      }
    } else {
      // Add to group
      const { error } = await supabase
        .from('device_group_members')
        .insert({ device_id: deviceId, group_id: groupId });

      if (!error) {
        setDevices(devices.map(d =>
          d.id === deviceId
            ? { ...d, group_ids: [...(d.group_ids || []), groupId] }
            : d
        ));
        setGroups(groups.map(g =>
          g.id === groupId
            ? { ...g, device_count: (g.device_count || 0) + 1 }
            : g
        ));
      }
    }
  }

  function openEdit(group: DeviceGroup) {
    setEditingGroup(group);
    setFormData({
      name: group.name,
      description: group.description || '',
      color: group.color,
    });
    setShowModal(true);
  }

  function resetForm() {
    setFormData({
      name: '',
      description: '',
      color: '#3B82F6',
    });
  }

  function isDeviceOnline(lastSeen: string) {
    return new Date(lastSeen) > new Date(Date.now() - 5 * 60 * 1000);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
      </div>
    );
  }

  const groupDevices = selectedGroup
    ? devices.filter(d => d.group_ids?.includes(selectedGroup.id))
    : [];

  const unassignedDevices = devices.filter(d => !d.group_ids?.length);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="w-7 h-7 text-red-500" />
            Device Groups
          </h1>
          <p className="text-gray-600 mt-1">Organize devices by department, team, or location</p>
        </div>
        <button
          onClick={() => { resetForm(); setEditingGroup(null); setShowModal(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Create Group
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Groups List */}
        <div className="lg:col-span-1 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Groups</h2>

          {groups.length === 0 ? (
            <div className="bg-white rounded-xl border p-8 text-center">
              <FolderOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No groups created yet</p>
              <button
                onClick={() => { resetForm(); setShowModal(true); }}
                className="mt-4 text-red-600 hover:text-red-700 font-medium"
              >
                Create your first group
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {groups.map((group) => (
                <div
                  key={group.id}
                  onClick={() => setSelectedGroup(group)}
                  className={`bg-white rounded-xl border p-4 cursor-pointer transition-all ${
                    selectedGroup?.id === group.id
                      ? 'ring-2 ring-red-500 border-transparent'
                      : 'hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: group.color }}
                      />
                      <div>
                        <p className="font-medium text-gray-900">{group.name}</p>
                        <p className="text-sm text-gray-500">
                          {group.device_count} device{group.device_count !== 1 ? 's' : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => { e.stopPropagation(); openEdit(group); }}
                        className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteGroup(group.id); }}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </div>
                  {group.description && (
                    <p className="text-sm text-gray-500 mt-2">{group.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Unassigned Devices Count */}
          {unassignedDevices.length > 0 && (
            <div
              onClick={() => setSelectedGroup(null)}
              className={`bg-gray-50 rounded-xl border border-dashed p-4 cursor-pointer transition-all ${
                selectedGroup === null && groups.length > 0
                  ? 'ring-2 ring-gray-400 border-transparent'
                  : 'hover:border-gray-400'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded-full bg-gray-400" />
                <div>
                  <p className="font-medium text-gray-700">Unassigned</p>
                  <p className="text-sm text-gray-500">
                    {unassignedDevices.length} device{unassignedDevices.length !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Devices Panel */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Monitor className="w-5 h-5 text-gray-500" />
                {selectedGroup ? (
                  <span>
                    Devices in{' '}
                    <span style={{ color: selectedGroup.color }}>{selectedGroup.name}</span>
                  </span>
                ) : (
                  'All Devices'
                )}
              </h2>
            </div>

            <div className="divide-y max-h-[600px] overflow-auto">
              {(selectedGroup ? devices : devices).map((device) => {
                const isInSelectedGroup = selectedGroup
                  ? (device.group_ids?.includes(selectedGroup.id) ?? false)
                  : false;
                const online = isDeviceOnline(device.last_seen);

                return (
                  <div key={device.id} className="p-4 hover:bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-3 h-3 rounded-full ${online ? 'bg-green-500' : 'bg-gray-300'}`} />
                      <div>
                        <p className="font-medium text-gray-900">
                          {device.device_name || device.hostname}
                        </p>
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                          <span>{device.os}</span>
                          {device.group_ids && device.group_ids.length > 0 && (
                            <>
                              <span>•</span>
                              <div className="flex gap-1">
                                {device.group_ids.map((gid) => {
                                  const g = groups.find(gr => gr.id === gid);
                                  return g ? (
                                    <span
                                      key={gid}
                                      className="px-1.5 py-0.5 rounded text-xs font-medium"
                                      style={{ backgroundColor: g.color + '20', color: g.color }}
                                    >
                                      {g.name}
                                    </span>
                                  ) : null;
                                })}
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {selectedGroup && (
                      <button
                        onClick={() => toggleDeviceInGroup(device.id, selectedGroup.id, isInSelectedGroup)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                          isInSelectedGroup
                            ? 'bg-red-100 text-red-700 hover:bg-red-200'
                            : 'bg-green-100 text-green-700 hover:bg-green-200'
                        }`}
                      >
                        {isInSelectedGroup ? 'Remove' : 'Add'}
                      </button>
                    )}

                    {!selectedGroup && groups.length > 0 && (
                      <div className="flex gap-1">
                        {groups.map((g) => {
                          const isMember = device.group_ids?.includes(g.id) ?? false;
                          return (
                            <button
                              key={g.id}
                              onClick={() => toggleDeviceInGroup(device.id, g.id, isMember)}
                              className={`w-6 h-6 rounded-full border-2 transition-all ${
                                isMember
                                  ? 'border-transparent'
                                  : 'border-gray-200 hover:border-gray-400'
                              }`}
                              style={{
                                backgroundColor: isMember ? g.color : 'transparent',
                              }}
                              title={isMember ? `Remove from ${g.name}` : `Add to ${g.name}`}
                            >
                              {isMember && <UserCheck className="w-3 h-3 text-white mx-auto" />}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}

              {devices.length === 0 && (
                <div className="p-12 text-center text-gray-500">
                  <Monitor className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p>No devices registered yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md m-4">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">
                {editingGroup ? 'Edit Group' : 'Create New Group'}
              </h2>
              <button
                onClick={() => { setShowModal(false); setEditingGroup(null); }}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Group Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  placeholder="e.g., Engineering Team"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Description (optional)</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  placeholder="Brief description of this group"
                />
              </div>

              {/* Color */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <div className="flex items-center gap-2">
                    <Palette className="w-4 h-4" />
                    Color
                  </div>
                </label>
                <div className="flex gap-2 flex-wrap">
                  {colorOptions.map((color) => (
                    <button
                      key={color.value}
                      onClick={() => setFormData({ ...formData, color: color.value })}
                      className={`w-8 h-8 rounded-full border-2 transition-all ${
                        formData.color === color.value
                          ? 'border-gray-900 scale-110'
                          : 'border-transparent hover:scale-105'
                      }`}
                      style={{ backgroundColor: color.value }}
                      title={color.label}
                    />
                  ))}
                </div>
              </div>

              {/* Preview */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-2">Preview</p>
                <div className="flex items-center gap-3">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: formData.color }}
                  />
                  <span className="font-medium text-gray-900">
                    {formData.name || 'Group Name'}
                  </span>
                </div>
              </div>
            </div>

            <div className="p-6 border-t bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => { setShowModal(false); setEditingGroup(null); }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveGroup}
                disabled={!formData.name}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4" />
                {editingGroup ? 'Update Group' : 'Create Group'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
