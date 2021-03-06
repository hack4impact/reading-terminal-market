var gulp = require('gulp'),
  livereload = require('gulp-livereload');

gulp.task('trigger', function() {
  console.log('trigger reload');
  gulp.src('app/static/styles/app.css').pipe(livereload());
  gulp.src('app/templates/**/*.html').pipe(livereload());
});

gulp.task('watch', function() {
  livereload.listen();
  console.log('eyyy');
  gulp.watch('app/assets/styles/*.scss', ['trigger']);
  gulp.watch('app/templates/**/*.html', ['trigger']);
})

gulp.task('default', function() {
  gulp.start('watch')
})