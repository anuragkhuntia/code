---
- name: install application
  hosts: all
  become: yes
  tasks:
    - name: install 
      apt: 
        name: nginx
        state: present

    - name: start
      service:
        name: nginx
        state: started
        enabled: yes



