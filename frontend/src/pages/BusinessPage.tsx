// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUILD FIX
// 1. TYPES: Aligned state and API calls with BusinessProfile interface.
// 2. STATE: Handles null profile initialization gracefully.
// 3. UI: Updated input fields to match BusinessProfileUpdate type.

import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Building2, Mail, Phone, MapPin, Globe, Palette, Save, Upload, Loader2, CreditCard } from 'lucide-react';
import { apiService } from '../services/api';
import { BusinessProfile, BusinessProfileUpdate } from '../data/types';
import { useTranslation } from 'react-i18next';

const BusinessPage: React.FC = () => {
  const { t } = useTranslation();
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form State
  const [formData, setFormData] = useState<BusinessProfileUpdate>({
    firm_name: '',
    email_public: '',
    phone: '',
    address: '',
    city: '',
    website: '',
    tax_id: '',
    branding_color: '#1f2937'
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const data = await apiService.getBusinessProfile();
      setProfile(data);
      // Initialize form with fetched data
      setFormData({
        firm_name: data.firm_name,
        email_public: data.email_public || '',
        phone: data.phone || '',
        address: data.address || '',
        city: data.city || '',
        website: data.website || '',
        tax_id: data.tax_id || '',
        branding_color: data.branding_color || '#1f2937'
      });
    } catch (error) {
      console.error("Failed to load business profile:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updatedProfile = await apiService.updateBusinessProfile(formData);
      setProfile(updatedProfile);
      alert(t('settings.successMessage', 'Profili u përditësua me sukses!'));
    } catch (error) {
      console.error("Update failed:", error);
      alert(t('error.generic', 'Gabim gjatë ruajtjes.'));
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setSaving(true);
      const updatedProfile = await apiService.uploadBusinessLogo(file);
      setProfile(updatedProfile);
    } catch (error) {
      console.error("Logo upload failed:", error);
      alert(t('error.uploadFailed', 'Ngarkimi i logos dështoi.'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-96"><Loader2 className="w-8 h-8 animate-spin text-primary-start" /></div>;
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }} 
      animate={{ opacity: 1, y: 0 }} 
      className="max-w-4xl mx-auto py-8 px-4"
    >
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">{t('business.title', 'Profili i Biznesit')}</h1>
        <p className="text-gray-400">{t('business.subtitle', 'Menaxhoni identitetin e zyrës suaj ligjore.')}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left Column: Logo & Branding */}
        <div className="space-y-6">
          <div className="bg-background-dark border border-glass-edge rounded-2xl p-6 text-center">
            <div className="relative w-32 h-32 mx-auto mb-4 bg-background-light rounded-full flex items-center justify-center overflow-hidden border-2 border-dashed border-gray-600 group hover:border-primary-start transition-colors">
              {profile?.logo_url ? (
                <img src={profile.logo_url} alt="Logo" className="w-full h-full object-cover" />
              ) : (
                <Building2 className="w-12 h-12 text-gray-500" />
              )}
              <div className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                <Upload className="w-6 h-6 text-white" />
              </div>
            </div>
            <input type="file" ref={fileInputRef} onChange={handleLogoUpload} className="hidden" accept="image/*" />
            <h3 className="text-lg font-semibold text-white mb-1">{formData.firm_name || 'Emri i Zyrës'}</h3>
            <p className="text-sm text-gray-400">Logo & Identiteti Vizual</p>
          </div>

          <div className="bg-background-dark border border-glass-edge rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Palette className="w-5 h-5 text-accent-start" /> Branding
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Ngjyra Kryesore (HEX)</label>
                <div className="flex gap-3">
                  <input 
                    type="color" 
                    name="branding_color"
                    value={formData.branding_color}
                    onChange={handleInputChange}
                    className="h-10 w-16 bg-transparent border-0 rounded cursor-pointer"
                  />
                  <input 
                    type="text" 
                    name="branding_color"
                    value={formData.branding_color}
                    onChange={handleInputChange}
                    className="flex-1 bg-background-light border border-glass-edge rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Details Form */}
        <div className="md:col-span-2">
          <form onSubmit={handleSubmit} className="bg-background-dark border border-glass-edge rounded-2xl p-6 space-y-6">
            
            <div className="grid grid-cols-1 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Emri i Zyrës Ligjore</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                  <input 
                    type="text" 
                    name="firm_name"
                    value={formData.firm_name}
                    onChange={handleInputChange}
                    className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2.5 text-white focus:ring-2 focus:ring-primary-start outline-none"
                    placeholder="Juristi Partners Sh.p.k"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Email Publik</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                    <input 
                      type="email" 
                      name="email_public"
                      value={formData.email_public}
                      onChange={handleInputChange}
                      className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2.5 text-white focus:ring-2 focus:ring-primary-start outline-none"
                      placeholder="contact@example.com"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Telefon</label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                    <input 
                      type="text" 
                      name="phone"
                      value={formData.phone}
                      onChange={handleInputChange}
                      className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2.5 text-white focus:ring-2 focus:ring-primary-start outline-none"
                      placeholder="+383 44 ..."
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Adresa</label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                  <input 
                    type="text" 
                    name="address"
                    value={formData.address}
                    onChange={handleInputChange}
                    className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2.5 text-white focus:ring-2 focus:ring-primary-start outline-none"
                    placeholder="Rruga, Nr..."
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Qyteti</label>
                  <input 
                    type="text" 
                    name="city"
                    value={formData.city}
                    onChange={handleInputChange}
                    className="w-full bg-background-light border border-glass-edge rounded-xl px-4 py-2.5 text-white focus:ring-2 focus:ring-primary-start outline-none"
                    placeholder="Prishtinë"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Website</label>
                  <div className="relative">
                    <Globe className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                    <input 
                      type="text" 
                      name="website"
                      value={formData.website}
                      onChange={handleInputChange}
                      className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2.5 text-white focus:ring-2 focus:ring-primary-start outline-none"
                      placeholder="www.example.com"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Numri Fiskal / NUI</label>
                <div className="relative">
                  <CreditCard className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                  <input 
                    type="text" 
                    name="tax_id"
                    value={formData.tax_id}
                    onChange={handleInputChange}
                    className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2.5 text-white focus:ring-2 focus:ring-primary-start outline-none"
                    placeholder="123456789"
                  />
                </div>
              </div>
            </div>

            <div className="pt-4 flex justify-end">
              <button 
                type="submit" 
                disabled={saving}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold hover:shadow-lg transition-all disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                {t('general.save', 'Ruaj Ndryshimet')}
              </button>
            </div>

          </form>
        </div>
      </div>
    </motion.div>
  );
};

export default BusinessPage;