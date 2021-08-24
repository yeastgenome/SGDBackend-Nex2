lock '3.8.0'

set :application, 'SGDBackend-NEX2'

set :repo_url, 'git://github.com/yeastgenome/SGDBackend-Nex2.git'
set :branch, ENV['BRANCH'] || $1 if `git branch` =~ /\* (\S+)\s/m
set :deploy_to, '/data/www/' + fetch(:application)
set :pty, true
set :user, 'deploy'
set :tmp_dir, "/home/deploy/tmp"

set :default_stage, "dev"

set :keep_releases, 5
set :format, :pretty
set :log_level, :debug

namespace :deploy do
  after :finishing, :config
  after :finishing, :build
  after :finishing, :copy_js
  after :finishing, :restart
end
